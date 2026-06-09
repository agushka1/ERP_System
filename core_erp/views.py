from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.core.exceptions import ValidationError
from django.contrib import messages
from .services import UserService, ShopService
from .models import TransactionHistory, Product, Order

Employee = get_user_model()


def login_view(request):
    """Контроллер для авторизации сотрудников в ERP-системе."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    error_message = None

    if request.method == 'POST':
        username_input = request.POST.get('username')
        password_input = request.POST.get('password')

        user = authenticate(request, username=username_input, password=password_input)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            error_message = "Неверное имя пользователя или пароль."

    return render(request, 'core_erp/login.html', {'error': error_message})


def logout_view(request):
    """Контроллер для безопасного выхода из системы и удаления сессии."""
    logout(request)
    return redirect('login')


def dashboard_view(request):
    """Главная страница: витрина команды и отправка монет благодарности."""
    if not request.user.is_authenticated:
        return redirect('login')

    # Обработка отправки монет из карточки сотрудника
    if request.method == 'POST' and 'action_transfer' in request.POST:
        receiver_id = request.POST.get('receiver_id')
        amount_raw = request.POST.get('amount', '0')
        comment = request.POST.get('comment', '').strip()

        try:
            amount = Decimal(amount_raw)
            # Вызываем ACID-сервис для безопасного перевода монет
            UserService.transfer_currency(
                sender_id=request.user.id,
                receiver_id=int(receiver_id),
                amount=amount,
                comment=comment
            )
            messages.success(request, "Валюта успешно отправлена коллеге!")
        except (InvalidOperation, ValueError):
            messages.error(request, "Некорректная сумма перевода.")
        except ValidationError as e:
            messages.error(request, e.message)

        return redirect('dashboard')

    colleagues = Employee.objects.exclude(id=request.user.id).order_by('first_name')

    context = {
        'user': request.user,
        'colleagues': colleagues,
    }
    return render(request, 'core_erp/dashboard.html', context)


def balance_view(request):
    """Страница «Мой баланс»: детальные счета и история операций."""
    if not request.user.is_authenticated:
        return redirect('login')

    history = TransactionHistory.objects.filter(
        sender=request.user
    ) | TransactionHistory.objects.filter(
        receiver=request.user
    )
    history = history.order_by('-created_at')

    context = {
        'user': request.user,
        'history': history
    }
    return render(request, 'core_erp/balance.html', context)


def shop_view(request):
    """Страница магазина мерча с добавлением в корзину сессии."""
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST' and 'action_add_to_cart' in request.POST:
        product_id = request.POST.get('product_id')
        cart = request.session.get('cart', {})
        cart[product_id] = cart.get(product_id, 0) + 1
        request.session['cart'] = cart
        messages.success(request, "Товар успешно добавлен в корзину!")
        return redirect('shop')

    products = Product.objects.all().order_by('name')

    context = {
        'user': request.user,
        'products': products
    }
    return render(request, 'core_erp/shop.html', context)


def cart_view(request):
    """Страница просмотра корзины и истории личных заказов покупателя."""
    if not request.user.is_authenticated:
        return redirect('login')

    cart = request.session.get('cart', {})

    # 1. Оплата всей корзины (базовая рабочая ACID-логика)
    if request.method == 'POST' and 'action_checkout' in request.POST:
        try:
            ShopService.checkout_cart(employee_id=request.user.id, cart_data=cart)
            request.session['cart'] = {}
            messages.success(request, "🛒 Заказ успешно оформлен! Он появился в списке под корзиной.")
            return redirect('cart') # Перенаправляем сюда же, чтобы увидеть новый заказ
        except ValidationError as e:
            messages.error(request, e.message)
            return redirect('cart')

    # 2. Очистка корзины
    if request.method == 'POST' and 'action_clear' in request.POST:
        request.session['cart'] = {}
        messages.success(request, "Корзина успешно очищена.")
        return redirect('cart')

    # Собираем текущие товары в корзине для отображения
    cart_items = []
    total_cart_price = Decimal('0.00')

    if cart:
        products = Product.objects.filter(id__in=[int(pid) for pid in cart.keys()])
        for prod in products:
            quantity = cart.get(str(prod.id), 0)
            item_total = prod.price * quantity
            total_cart_price += item_total
            cart_items.append({
                'product': prod,
                'quantity': quantity,
                'item_total': item_total
            })
    my_orders = Order.objects.filter(employee=request.user).order_by('-created_at')

    context = {
        'user': request.user,
        'cart_items': cart_items,
        'total_cart_price': total_cart_price,
        'my_orders': my_orders # Прокидываем заказы в HTML-шаблон
    }
    return render(request, 'core_erp/cart.html', context)



def admin_add_product_view(request):
    """Страница админки: Добавление нового товара."""
    if not request.user.is_authenticated or request.user.role != Employee.Role.ADMIN:
        return redirect('dashboard')

    if request.method == 'POST' and 'action_add_product' in request.POST:
        name = request.POST.get('name', '').strip()
        price_raw = request.POST.get('price', '0')
        stock_raw = request.POST.get('stock', '0')
        image = request.FILES.get('image')
        try:
            price = Decimal(price_raw)
            stock = int(stock_raw)
            Product.objects.create(name=name, price=price, stock=stock, image=image)
            messages.success(request, f"Товар '{name}' успешно добавлен!")
        except (InvalidOperation, ValueError):
            messages.error(request, "Некорректно указана цена или количество.")
        return redirect('admin_add_product')

    return render(request, 'core_erp/admin_add_product.html', {'user': request.user})


def admin_currency_view(request):
    """Страница админки: Начисление средств и штрафы."""
    if not request.user.is_authenticated or request.user.role != Employee.Role.ADMIN:
        return redirect('dashboard')

    if request.method == 'POST':
        employee_id = request.POST.get('employee_id')
        amount_raw = request.POST.get('amount', '0')
        balance_type = request.POST.get('balance_type')
        comment = request.POST.get('comment', '').strip()
        action = request.POST.get('action')
        try:
            amount = Decimal(amount_raw)
            if action == 'bonus':
                UserService.admin_add_bonus(request.user, int(employee_id), amount, balance_type, comment)
                messages.success(request, "Премия успешно зачислена!")
            elif action == 'fine':
                UserService.admin_apply_fine(request.user, int(employee_id), amount, balance_type, comment)
                messages.success(request, "Штраф успешно списан.")
        except (InvalidOperation, ValueError):
            messages.error(request, "Введена некорректная сумма.")
        except ValidationError as e:
            messages.error(request, e.message)
        return redirect('admin_currency')

    all_employees = Employee.objects.all().order_by('first_name')
    return render(request, 'core_erp/admin_currency.html', {'user': request.user, 'all_employees': all_employees})


def admin_orders_view(request):
    """Страница админки: Учет магазина и поэтапное изменение статусов заказов."""
    if not request.user.is_authenticated or request.user.role != Employee.Role.ADMIN:
        return redirect('dashboard')

    if request.method == 'POST' and 'action_change_status' in request.POST:
        order_id = request.POST.get('order_id')
        new_status = request.POST.get('new_status')  # Получаем выбранный админом статус

        try:
            order = Order.objects.get(id=int(order_id))
            if new_status in Order.Status.values:
                order.status = new_status
                order.save()
                messages.success(request,
                                 f"Статус заказа #{order.id} успешно изменен на '{order.get_status_display()}'!")
            else:
                messages.error(request, "Указан неверный статус.")
        except Order.DoesNotExist:
            messages.error(request, "Заказ не найден.")

        return redirect('admin_orders')

    all_orders = Order.objects.all().order_by('-created_at')
    return render(request, 'core_erp/admin_orders.html', {'user': request.user, 'all_orders': all_orders})
