import os
from decimal import Decimal
from django.apps import AppConfig
from django.db import transaction


@transaction.atomic
def add_weekly_coins_task():
    from .models import Employee, TransactionHistory

    amount = Decimal("500.00")
    comment_text = "Еженедельное автоматическое начисление монет"

    # Блокируем строки всех сотрудников с сортировкой по ID для защиты от Deadlock
    employees = Employee.objects.select_for_update().order_by("id")

    for employee in employees:
        # Начисляем монеты на баланс для передачи
        employee.transferable_balance += amount
        employee.save()

        # Создаем запись в истории транзакций
        TransactionHistory.objects.create(
            transaction_type=TransactionHistory.Type.BONUS,  # Ставим тип "Премия от админа"
            sender=None,  # Оставляем None, чтобы сработал твой HTML шаблон ("Администрации")
            receiver=employee,
            amount=amount,
            comment=comment_text
        )


class CoreErpConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core_erp"

    def ready(self):
        # Проверяем хук, чтобы код не запускался дважды при автоперезагрузке Django
        if os.environ.get("RUN_MAIN") == "true":
            from apscheduler.schedulers.background import BackgroundScheduler
            from django_apscheduler.jobstores import DjangoJobStore

            # Настраиваем и запускаем наш будильник
            scheduler = BackgroundScheduler()
            scheduler.add_jobstore(DjangoJobStore(), "default")

            scheduler.add_job(
                add_weekly_coins_task,
                trigger="cron",
                day_of_week="mon",
                hour=0,
                minute=0,
                id="add_weekly_coins_job",
                max_instances=1,
                replace_existing=True,
            )

            scheduler.start()
