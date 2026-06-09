from django.contrib.auth.models import AbstractUser
from django.db import models


class Employee(AbstractUser):
    """Кастомная модель пользователя, объединяющая аккаунт Django и профиль сотрудника."""

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Администратор'
        EMPLOYEE = 'EMPLOYEE', 'Сотрудник'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.EMPLOYEE,
        verbose_name="Роль"
    )

    transferable_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=500.00,
        verbose_name="Баланс для передачи"
    )

    spendable_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Баланс для покупок"
    )

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"

    def __str__(self):
        return f"{self.username} [{self.get_role_display()}] (Передача: {self.transferable_balance} | Покупки: {self.spendable_balance})"


class Product(models.Model):
    """Модель товара на складе."""
    name = models.CharField(max_length=255, verbose_name="Название товара")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    stock = models.PositiveIntegerField(default=0, verbose_name="Количество на складе")
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Фотография товара")

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def __str__(self):
        return f"{self.name} ({self.stock} шт. по {self.price})"


class TransactionHistory(models.Model):
    """История всех движений валюты в системе для полного аудита."""

    class Type(models.TextChoices):
        TRANSFER = 'TRANSFER', 'Перевод коллеге'
        PURCHASE = 'PURCHASE', 'Покупка товара'
        BONUS = 'BONUS', 'Премия от админа'
        FINE = 'FINE', 'Штраф от админа'

    transaction_type = models.CharField(
        max_length=15,
        choices=Type.choices,
        verbose_name="Тип операции"
    )

    sender = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_transactions',
        verbose_name="Отправитель"
    )

    receiver = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_transactions',
        verbose_name="Получатель"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Купленный товар"
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма")
    comment = models.TextField(blank=True, verbose_name="Комментарий к операции")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время")

    class Meta:
        verbose_name = "История транзакции"
        verbose_name_plural = "История транзакций"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} на сумму {self.amount} ({self.created_at:%Y-%m-%d %H:%M})"


class Order(models.Model):
    """Модель заказа для детального учета и выдачи мерча."""

    class Status(models.TextChoices):
        PAID = 'PAID', 'Оплачен (Собирается)'
        READY = 'READY', 'Ожидает получения (В офисе)'
        DELIVERED = 'DELIVERED', 'Выдан сотруднику'

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name="Сотрудник"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name="Товар"
    )
    quantity = models.PositiveIntegerField(
        verbose_name="Количество"
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Общая стоимость"
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PAID,  # ПОЧИНИЛИ: Теперь по дефолту заказ "Оплачен"
        verbose_name="Статус заказа"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата заказа"
    )

    class Meta:
        verbose_name = "Заказ мерча"
        verbose_name_plural = "Заказы мерча"
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ #{self.id} — {self.product.name} ({self.quantity} шт.) для {self.employee.first_name}"