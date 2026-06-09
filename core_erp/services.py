from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Employee, Product, TransactionHistory


class UserService:
    """Сервис для управления балансами сотрудников (Премии, Штрафы, Переводы)."""

    @staticmethod
    @transaction.atomic
    def transfer_currency(sender_id: int, receiver_id: int, amount: Decimal, comment: str) -> TransactionHistory:
        """Перевод валюты от сотрудника к сотруднику с ACID защитой."""
        if amount <= 0:
            raise ValidationError("Сумма перевода должна быть больше нуля.")
        if sender_id == receiver_id:
            raise ValidationError("Нельзя переводить валюту самому себе.")

        # Сортируем ID для предотвращения взаимной блокировки (Deadlock)
        ids = sorted([sender_id, receiver_id])
        employees = {e.id: e for e in Employee.objects.select_for_update().filter(id__in=ids)}

        sender = employees.get(sender_id)
        receiver = employees.get(receiver_id)

        if sender.transferable_balance < amount:
            raise ValidationError(f"Недостаточно средств. Ваш баланс для передачи: {sender.transferable_balance}")

        # Списание и зачисление
        sender.transferable_balance -= amount
        receiver.spendable_balance += amount

        sender.save()
        receiver.save()

        return TransactionHistory.objects.create(
            transaction_type=TransactionHistory.Type.TRANSFER,
            sender=sender,
            receiver=receiver,
            amount=amount,
            comment=comment
        )

    @staticmethod
    @transaction.atomic
    def admin_add_bonus(admin: Employee, employee_id: int, amount: Decimal, balance_type: str,
                        comment: str) -> TransactionHistory:
        """Начисление премии администратором."""
        if amount <= 0:
            raise ValidationError("Сумма премии должна быть больше нуля.")

        employee = Employee.objects.select_for_update().get(id=employee_id)

        if balance_type == 'transferable':
            employee.transferable_balance += amount
        else:
            employee.spendable_balance += amount

        employee.save()

        return TransactionHistory.objects.create(
            transaction_type=TransactionHistory.Type.BONUS,
            sender=admin,
            receiver=employee,
            amount=amount,
            comment=comment
        )

    @staticmethod
    @transaction.atomic
    def admin_apply_fine(admin: Employee, employee_id: int, amount: Decimal, balance_type: str,
                         comment: str) -> TransactionHistory:
        """Списание штрафа администратором."""
        if amount <= 0:
            raise ValidationError("Сумма штрафа должна быть больше нуля.")

        employee = Employee.objects.select_for_update().get(id=employee_id)

        if balance_type == 'transferable':
            if employee.transferable_balance < amount:
                raise ValidationError("У сотрудника недостаточно средств на балансе для передачи.")
            employee.transferable_balance -= amount
        else:
            if employee.spendable_balance < amount:
                raise ValidationError("У сотрудника недостаточно средств на балансе для покупок.")
            employee.spendable_balance -= amount

        employee.save()

        return TransactionHistory.objects.create(
            transaction_type=TransactionHistory.Type.FINE,
            sender=admin,
            receiver=employee,
            amount=amount,
            comment=comment
        )


class ShopService:
    """Сервис для работы с магазином и комплексными заказами (Корзиной)."""

    @staticmethod
    @transaction.atomic
    def buy_product(employee_id: int, product_id: int) -> TransactionHistory:
        """Покупка одного товара."""
        employee = Employee.objects.select_for_update().get(id=employee_id)
        product = Product.objects.select_for_update().get(id=product_id)

        if product.stock <= 0:
            raise ValidationError(f"Товара '{product.name}' нет в наличии.")
        if employee.spendable_balance < product.price:
            raise ValidationError(f"Недостаточно средств. Нужно: {product.price}")

        employee.spendable_balance -= product.price
        product.stock -= 1

        employee.save()
        product.save()

        return TransactionHistory.objects.create(
            transaction_type=TransactionHistory.Type.PURCHASE,
            sender=employee,
            product=product,
            amount=product.price,
            comment=f"Покупка товара: {product.name}"
        )

    @staticmethod
    @transaction.atomic
    def checkout_cart(employee_id: int, cart_data: dict):
        """Оформление всей корзины целиком внутри одной ACID-транзакции с созданием Заказов."""
        # Подключаем модель Order локально или сверху файла, если забыли
        from .models import Order

        if not cart_data:
            raise ValidationError("Ваша корзина пуста.")

        employee = Employee.objects.select_for_update().get(id=employee_id)

        total_price = Decimal('0.00')
        products_to_update = []
        histories_to_create = []
        orders_to_create = []

        product_ids = [int(pid) for pid in cart_data.keys()]
        products = {p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids)}

        for p_id, quantity in cart_data.items():
            product = products.get(int(p_id))
            if not product:
                raise ValidationError("Один из товаров в корзине не найден в базе данных.")

            if product.stock < quantity:
                raise ValidationError(f"Недостаточно товара '{product.name}' на складе. Доступно: {product.stock} шт.")

            item_cost = product.price * quantity
            total_price += item_cost

            # Уменьшаем остаток на складе товара
            product.stock -= quantity
            products_to_update.append(product)

            # 1. Готовим запись для финансового аудита валюты
            histories_to_create.append(
                TransactionHistory(
                    transaction_type=TransactionHistory.Type.PURCHASE,
                    sender=employee,
                    product=product,
                    amount=item_cost,
                    comment=f"Покупка товара: {product.name} (Кол-во: {quantity} шт.)"
                )
            )

            # 2. Готовим реальный заказ для склада со статусом PENDING (Ожидает выдачи)
            orders_to_create.append(
                Order(
                    employee=employee,
                    product=product,
                    quantity=quantity,
                    total_price=item_cost,
                    status=Order.Status.PENDING
                )
            )

        if employee.spendable_balance < total_price:
            raise ValidationError(
                f"Недостаточно средств. Стоимость корзины: {total_price} 🪙, у вас: {employee.spendable_balance} 🪙")

        # Применяем финансовые списания
        employee.spendable_balance -= total_price
        employee.save()

        # Обновляем остатки на складе
        for prod in products_to_update:
            prod.save()

        # Массово и безопасно сохраняем финансовые логи и складские заказы (ACID)
        TransactionHistory.objects.bulk_create(histories_to_create)
        Order.objects.bulk_create(orders_to_create)
