from django.db import migrations
from django.contrib.auth.hashers import make_password


def create_all_ten_employees(apps, schema_editor):
    Employee = apps.get_model('core_erp', 'Employee')

    # Список из всех 10 сотрудников
    employees_list = [
        # 1. Администратор
        {
            "username": "admin_ivan", "name": "Иван (Админ)", "role": "ADMIN",
            "is_staff": True, "is_superuser": True, "transferable": 1000.00
        },
        # 2-10. Девять обычных сотрудников со стартовым балансом 500
        {"username": "user_anna", "name": "Анна Смирнова", "role": "EMPLOYEE", "is_staff": False, "is_superuser": False,
         "transferable": 500.00},
        {"username": "user_petr", "name": "Петр Петров", "role": "EMPLOYEE", "is_staff": False, "is_superuser": False,
         "transferable": 500.00},
        {"username": "user_elena", "name": "Елена Козлова", "role": "EMPLOYEE", "is_staff": False,
         "is_superuser": False, "transferable": 500.00},
        {"username": "user_dmitry", "name": "Дмитрий Волков", "role": "EMPLOYEE", "is_staff": False,
         "is_superuser": False, "transferable": 500.00},
        {"username": "user_olga", "name": "Ольга Кузнецова", "role": "EMPLOYEE", "is_staff": False,
         "is_superuser": False, "transferable": 500.00},
        {"username": "user_alex", "name": "Алексей Морозов", "role": "EMPLOYEE", "is_staff": False,
         "is_superuser": False, "transferable": 500.00},
        {"username": "user_maria", "name": "Мария Федорова", "role": "EMPLOYEE", "is_staff": False,
         "is_superuser": False, "transferable": 500.00},
        {"username": "user_sergey", "name": "Сергей Попов", "role": "EMPLOYEE", "is_staff": False,
         "is_superuser": False, "transferable": 500.00},
        {"username": "user_natalia", "name": "Наталья Васильева", "role": "EMPLOYEE", "is_staff": False,
         "is_superuser": False, "transferable": 500.00},
    ]

    for user_data in employees_list:
        if not Employee.objects.filter(username=user_data["username"]).exists():
            Employee.objects.create(
                username=user_data["username"],
                first_name=user_data["name"],
                role=user_data["role"],
                is_staff=user_data["is_staff"],
                is_superuser=user_data["is_superuser"],
                transferable_balance=user_data["transferable"],
                spendable_balance=0.00,
                password=make_password("password123")  # Один общий пароль для тестов
            )


def remove_all_ten_employees(apps, schema_editor):
    Employee = apps.get_model('core_erp', 'Employee')
    usernames = [
        "admin_ivan", "user_anna", "user_petr", "user_elena", "user_dmitry",
        "user_olga", "user_alex", "user_maria", "user_sergey", "user_natalia"
    ]
    Employee.objects.filter(username__in=usernames).delete()


class Migration(migrations.Migration):
    dependencies = [
        # Указываем строго первую миграцию как родителя
        ('core_erp', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_all_ten_employees, reverse_code=remove_all_ten_employees),
    ]