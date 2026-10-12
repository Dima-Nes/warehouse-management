"""
inventory/management/commands/seed_warehouse_data.py
Команда автогенерации демонстрационных данных склада:
- 5 товарных категорий
- 5 поставщиков
- 25 реалистичных номенклатурных позиций
- 8 заказов на закупку в разных статусах (Создан, Отправлен, Выполнен, Отменён)
- 70+ складских проводок за последние 60 дней для красивых графиков аналитики

Студент: Нестерук Д.С., группа ПО-2409
"""

import datetime
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import CustomUser
from inventory.models import Category, Product, StockMovement
from suppliers.models import Supplier, PurchaseOrder, OrderItem


class Command(BaseCommand):
    help = 'Заполняет базу данных реалистичными демонстрационными данными (Итерация 5)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистить существующие товары, поставщики и операции перед заполнением'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Начало наполнения базы данных демонстрационными данными..."))

        if options['clear']:
            self.stdout.write("Очистка существующих данных...")
            StockMovement.objects.all().delete()
            OrderItem.objects.all().delete()
            PurchaseOrder.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            Supplier.objects.all().delete()
            self.stdout.write(self.style.WARNING("Данные очищены."))

        with transaction.atomic():
            # 1. Получаем или создаём пользователей для авторства операций
            admin_user, _ = CustomUser.objects.get_or_create(
                username='admin',
                defaults={
                    'email': 'admin@warehouse.local',
                    'first_name': 'Дмитрий',
                    'last_name': 'Нестерук',
                    'role': CustomUser.Role.ADMIN,
                    'is_staff': True,
                    'is_superuser': True,
                }
            )
            if not admin_user.has_usable_password():
                admin_user.set_password('Admin1234!')
                admin_user.save()

            manager_user, _ = CustomUser.objects.get_or_create(
                username='manager',
                defaults={
                    'email': 'manager@warehouse.local',
                    'first_name': 'Алексей',
                    'last_name': 'Смирнов',
                    'role': CustomUser.Role.MANAGER,
                }
            )
            if not manager_user.has_usable_password():
                manager_user.set_password('Manager1234!')
                manager_user.save()

            staff_user, _ = CustomUser.objects.get_or_create(
                username='warehouse_staff',
                defaults={
                    'email': 'staff@warehouse.local',
                    'first_name': 'Иван',
                    'last_name': 'Ковалев',
                    'role': CustomUser.Role.WAREHOUSE_STAFF,
                }
            )
            if not staff_user.has_usable_password():
                staff_user.set_password('Staff1234!')
                staff_user.save()

            users_pool = [admin_user, manager_user, staff_user]

            # 2. Создание 5 категорий
            categories_data = [
                ('Электроника и компоненты', 'Микроконтроллеры, датчики, радиоэлектронные модули и блоки питания'),
                ('Кабельная продукция', 'Силовые и слаботочные кабели, патч-корды, гофротруба и разъемы'),
                ('Электроинструмент', 'Профессиональный инструмент, шуруповерты, измерительные приборы и оснастка'),
                ('Крепеж и метизы', 'Болты, гайки, саморезы, анкеры и монтажные металлические изделия'),
                ('Упаковка и логистика', 'Стрейч-пленка, гофрокороба, скотч, упаковочные пакеты и ленты'),
            ]

            categories = {}
            for name, desc in categories_data:
                cat, _ = Category.objects.get_or_create(name=name, defaults={'description': desc})
                categories[name] = cat

            self.stdout.write(f"Создано категорий: {len(categories)}")

            # 3. Создание 5 поставщиков
            suppliers_data = [
                {
                    'name': 'ООО «БелЭлектроСнаб»',
                    'inn': '193452819',
                    'contact_person': 'Андрей Сергеевич Воронов',
                    'phone': '+375 (17) 289-45-12',
                    'email': 'sales@belelektro.by',
                    'address': 'г. Минск, ул. Платонова, д. 20Б',
                    'notes': 'Основной поставщик электронных модулей. Срок доставки 3–5 рабочих дней.',
                },
                {
                    'name': 'ЗАО «КабельПромТех»',
                    'inn': '100984712',
                    'contact_person': 'Елена Викторовна Зинкевич',
                    'phone': '+375 (16) 245-88-90',
                    'email': 'order@kabelprom.by',
                    'address': 'г. Брест, ул. Коммерческая, д. 15',
                    'notes': 'Поставка кабельной продукции бухтами по 100м и 300м.',
                },
                {
                    'name': 'ОАО «ИнструментКомплект»',
                    'inn': '290817345',
                    'contact_person': 'Максим Юрьевич Григорьев',
                    'phone': '+375 (23) 250-11-22',
                    'email': 'info@instrument-gomel.by',
                    'address': 'г. Гомель, ул. Советская, д. 128',
                    'notes': 'Официальный дистрибьютор ручного и электроинструмента.',
                },
                {
                    'name': 'ООО «МетизТрейд Белая Русь»',
                    'inn': '192847561',
                    'contact_person': 'Денис Анатольевич Карпович',
                    'phone': '+375 (17) 366-99-44',
                    'email': 'zakaz@metiztrade.by',
                    'address': 'г. Минск, проспект Дзержинского, д. 104',
                    'notes': 'Оптовые поставки крепежа стандартов DIN и ГОСТ.',
                },
                {
                    'name': 'ЧПУП «ЕвроУпаковка»',
                    'inn': '490123984',
                    'contact_person': 'Ольга Николаевна Савицкая',
                    'phone': '+375 (15) 260-33-77',
                    'email': 'contact@euroupack.by',
                    'address': 'г. Гродно, ул. Горького, д. 89',
                    'notes': 'Производство гофротары и упаковочной стрейч-пленки.',
                },
            ]

            suppliers = {}
            for s_info in suppliers_data:
                name = s_info.pop('name')
                supp, _ = Supplier.objects.get_or_create(name=name, defaults=s_info)
                suppliers[name] = supp

            self.stdout.write(f"Создано поставщиков: {len(suppliers)}")

            # 4. Создание 25 реалистичных товаров
            products_data = [
                # Категория 1: Электроника
                ('EL-001', 'Микроконтроллер STM32F401 BlackPill', 'Электроника и компоненты', 'ООО «БелЭлектроСнаб»', 'pcs', '28.50', 45, 10, 'Отладочная плата ARM Cortex-M4'),
                ('EL-002', 'Модуль ESP32-WROOM-32 Wi-Fi/BLE', 'Электроника и компоненты', 'ООО «БелЭлектроСнаб»', 'pcs', '19.80', 80, 15, 'Двухъядерный микромодуль для IoT'),
                ('EL-003', 'Импульсный блок питания 12V 5A', 'Электроника и компоненты', 'ООО «БелЭлектроСнаб»', 'pcs', '42.00', 12, 10, 'Металлический корпус IP20 с защитой от КЗ'),
                ('EL-004', 'Преобразователь понижающий DC-DC LM2596', 'Электроника и компоненты', 'ООО «БелЭлектроСнаб»', 'pcs', '6.50', 4, 15, 'Регулируемый модуль с подстроечным резистором'), # Дефицит!
                ('EL-005', 'Датчик температуры и влажности DHT22', 'Электроника и компоненты', 'ООО «БелЭлектроСнаб»', 'pcs', '14.20', 0, 8, 'Цифровой откалиброванный датчик'), # Исчерпан!

                # Категория 2: Кабельная продукция
                ('CB-101', 'Кабель витая пара UTP Cat 5e 4PR бухта', 'Кабельная продукция', 'ЗАО «КабельПромТех»', 'box', '145.00', 8, 3, 'Медный проводник 0.51мм, 305 метров'),
                ('CB-102', 'Кабель силовой ВВГнг-LS 3x2.5', 'Кабельная продукция', 'ЗАО «КабельПромТех»', 'm', '3.20', 450, 100, 'Не поддерживающий горение, ГОСТ'),
                ('CB-103', 'Кабель силовой ВВГнг-LS 3x1.5', 'Кабельная продукция', 'ЗАО «КабельПромТех»', 'm', '2.10', 320, 100, 'Медный кабель для осветительных сетей'),
                ('CB-104', 'Разъем RJ-45 Cat 5e экранированный', 'Кабельная продукция', 'ЗАО «КабельПромТех»', 'pcs', '0.45', 600, 200, 'Коннектор с позолоченными контактами'),
                ('CB-105', 'Труба гофрированная ПВХ d20мм с протяжкой', 'Кабельная продукция', 'ЗАО «КабельПромТех»', 'm', '0.65', 50, 100, 'Бухта гофры легкого типа'), # Дефицит!

                # Категория 3: Электроинструмент
                ('TL-201', 'Дрель-шуруповерт аккумуляторная 18V', 'Электроинструмент', 'ОАО «ИнструментКомплект»', 'pcs', '285.00', 9, 4, 'Бесщеточный двигатель, 2 АКБ 4.0Ah в кейсе'),
                ('TL-202', 'Мультиметр цифровой профессиональный', 'Электроинструмент', 'ОАО «ИнструментКомплект»', 'pcs', '95.00', 14, 5, 'TrueRMS, измерение емкости и частоты'),
                ('TL-203', 'Набор отверток диэлектрических 1000V', 'Электроинструмент', 'ОАО «ИнструментКомплект»', 'box', '48.00', 18, 6, 'Сертификат VDE, 7 предметов'),
                ('TL-204', 'Паяльная станция термовоздушная', 'Электроинструмент', 'ОАО «ИнструментКомплект»', 'pcs', '190.00', 3, 5, 'Фен + паяльник с раздельной терморегуляцией'), # Дефицит!
                ('TL-205', 'Клещи обжимные кримпер для RJ-45/11', 'Электроинструмент', 'ОАО «ИнструментКомплект»', 'pcs', '36.50', 22, 5, 'Храповой механизм с лезвиями зачистки'),

                # Категория 4: Крепеж и метизы
                ('FS-301', 'Болт оцинкованный М8х30 DIN 933', 'Крепеж и метизы', 'ООО «МетизТрейд Белая Русь»', 'kg', '8.90', 75, 20, 'Класс прочности 8.8 с полной резьбой'),
                ('FS-302', 'Гайка шестигранная М8 DIN 934', 'Крепеж и метизы', 'ООО «МетизТрейд Белая Русь»', 'kg', '9.40', 60, 20, 'Оцинкованная углеродистая сталь'),
                ('FS-303', 'Шайба увеличенная М8 DIN 9021', 'Крепеж и метизы', 'ООО «МетизТрейд Белая Русь»', 'kg', '10.20', 50, 15, 'Кузовная оцинкованная шайба'),
                ('FS-304', 'Саморез по металлу со сверлом 4.2х19', 'Крепеж и метизы', 'ООО «МетизТрейд Белая Русь»', 'kg', '12.00', 6, 15, 'Оцинкованный наконечник-перо'), # Дефицит!
                ('FS-305', 'Дюбель нейлоновый универсальный 6х30', 'Крепеж и метизы', 'ООО «МетизТрейд Белая Русь»', 'box', '7.80', 40, 10, 'Упаковка 100 шт, распорный монтаж'),

                # Категория 5: Упаковка и логистика
                ('PK-401', 'Стрейч-пленка техническая 500мм 20мкм', 'Упаковка и логистика', 'ЧПУП «ЕвроУпаковка»', 'box', '21.50', 35, 10, 'Первичный гранулят, рулон 2.2 кг'),
                ('PK-402', 'Скотч упаковочный прозрачный 48мм х 66м', 'Упаковка и логистика', 'ЧПУП «ЕвроУпаковка»', 'pcs', '2.80', 120, 30, 'Акриловый клеевой слой высокой липкости'),
                ('PK-403', 'Гофроящик Т-23 400х300х200мм', 'Упаковка и логистика', 'ЧПУП «ЕвроУпаковка»', 'pcs', '1.65', 250, 50, 'Трехслойный бурый гофрокартон'),
                ('PK-404', 'Воздушно-пузырьковая пленка двухслойная', 'Упаковка и логистика', 'ЧПУП «ЕвроУпаковка»', 'm', '1.10', 0, 50, 'Рулон шириной 1.2м'), # Исчерпан!
                ('PK-405', 'Лента полипропиленовая упаковочная 12мм', 'Упаковка и логистика', 'ЧПУП «ЕвроУпаковка»', 'm', '0.08', 3500, 500, 'Бухта 3000м для обвязки паллет'),
            ]

            products = {}
            for sku, name, cat_name, supp_name, unit, price, qty, min_qty, desc in products_data:
                prod, _ = Product.objects.update_or_create(
                    sku=sku,
                    defaults={
                        'name': name,
                        'category': categories[cat_name],
                        'supplier': suppliers[supp_name],
                        'unit': unit,
                        'price': Decimal(price),
                        'quantity': qty,
                        'min_quantity': min_qty,
                        'description': desc,
                    }
                )
                products[sku] = prod

            self.stdout.write(f"Создано товаров: {len(products)}")

            # 5. Создание 8 заказов на закупку (PurchaseOrder + OrderItem)
            now = timezone.now()
            orders_config = [
                # 2 DRAFT
                {
                    'number': 'ЗК-2026-001',
                    'supplier': suppliers['ООО «БелЭлектроСнаб»'],
                    'status': PurchaseOrder.Status.DRAFT,
                    'planned_date': (now + datetime.timedelta(days=5)).date(),
                    'comment': 'Плановое пополнение микроконтроллеров и блоков питания',
                    'items': [
                        ('EL-001', 30, Decimal('26.00')),
                        ('EL-004', 50, Decimal('5.80')),
                        ('EL-005', 25, Decimal('13.00')),
                    ]
                },
                {
                    'number': 'ЗК-2026-002',
                    'supplier': suppliers['ЧПУП «ЕвроУпаковка»'],
                    'status': PurchaseOrder.Status.DRAFT,
                    'planned_date': (now + datetime.timedelta(days=7)).date(),
                    'comment': 'Срочная закупка упаковочной пленки',
                    'items': [
                        ('PK-404', 200, Decimal('0.95')),
                        ('PK-401', 20, Decimal('19.50')),
                    ]
                },
                # 2 SENT
                {
                    'number': 'ЗК-2026-003',
                    'supplier': suppliers['ЗАО «КабельПромТех»'],
                    'status': PurchaseOrder.Status.SENT,
                    'planned_date': (now + datetime.timedelta(days=3)).date(),
                    'comment': 'Счёт оплачен. Ожидается отгрузка перевозчиком.',
                    'items': [
                        ('CB-102', 300, Decimal('2.90')),
                        ('CB-105', 200, Decimal('0.58')),
                    ]
                },
                {
                    'number': 'ЗК-2026-004',
                    'supplier': suppliers['ОАО «ИнструментКомплект»'],
                    'status': PurchaseOrder.Status.SENT,
                    'planned_date': (now + datetime.timedelta(days=4)).date(),
                    'comment': 'Заказ подтверждён менеджером поставщика.',
                    'items': [
                        ('TL-204', 10, Decimal('175.00')),
                        ('TL-203', 15, Decimal('43.00')),
                    ]
                },
                # 3 DELIVERED
                {
                    'number': 'ЗК-2026-005',
                    'supplier': suppliers['ООО «МетизТрейд Белая Русь»'],
                    'status': PurchaseOrder.Status.DELIVERED,
                    'planned_date': (now - datetime.timedelta(days=15)).date(),
                    'comment': 'Поставка принята в полном объеме по ТТН-4591.',
                    'items': [
                        ('FS-301', 50, Decimal('8.00')),
                        ('FS-302', 40, Decimal('8.50')),
                        ('FS-304', 30, Decimal('10.80')),
                    ]
                },
                {
                    'number': 'ЗК-2026-006',
                    'supplier': suppliers['ООО «БелЭлектроСнаб»'],
                    'status': PurchaseOrder.Status.DELIVERED,
                    'planned_date': (now - datetime.timedelta(days=25)).date(),
                    'comment': 'Успешная поставка модулей ESP32.',
                    'items': [
                        ('EL-002', 100, Decimal('17.50')),
                        ('EL-003', 20, Decimal('38.00')),
                    ]
                },
                {
                    'number': 'ЗК-2026-007',
                    'supplier': suppliers['ЧПУП «ЕвроУпаковка»'],
                    'status': PurchaseOrder.Status.DELIVERED,
                    'planned_date': (now - datetime.timedelta(days=35)).date(),
                    'comment': 'Короба и скотч оприходованы.',
                    'items': [
                        ('PK-402', 200, Decimal('2.40')),
                        ('PK-403', 300, Decimal('1.45')),
                    ]
                },
                # 1 CANCELLED
                {
                    'number': 'ЗК-2026-008',
                    'supplier': suppliers['ЗАО «КабельПромТех»'],
                    'status': PurchaseOrder.Status.CANCELLED,
                    'planned_date': (now - datetime.timedelta(days=40)).date(),
                    'comment': 'Отменен ввиду изменения требований проектной документации.',
                    'items': [
                        ('CB-101', 15, Decimal('135.00')),
                    ]
                },
            ]

            created_orders_count = 0
            for o_data in orders_config:
                items_data = o_data.pop('items')
                num = o_data.pop('number')
                order, created = PurchaseOrder.objects.update_or_create(
                    number=num,
                    defaults=o_data
                )
                created_orders_count += 1
                for sku, qty, price in items_data:
                    OrderItem.objects.update_or_create(
                        order=order,
                        product=products[sku],
                        defaults={
                            'quantity': qty,
                            'purchase_price': price,
                        }
                    )

            self.stdout.write(f"Создано заказов на закупку: {created_orders_count}")

            # 6. Создание 75+ складских проводок за прошедшие два месяца
            random.seed(42)
            movements_created = 0

            # Создадим планомерные движения за каждый день последних 55 дней
            base_date = now - datetime.timedelta(days=55)

            # Ключевые ходовые товары для генерации активности
            active_skus = ['EL-001', 'EL-002', 'EL-004', 'CB-102', 'CB-104', 'TL-201', 'FS-301', 'PK-401', 'PK-402', 'PK-403']

            # Генерация серии реалистичных движений
            for day_offset in range(56):
                day_time = base_date + datetime.timedelta(days=day_offset, hours=random.randint(8, 18), minutes=random.randint(0, 59))

                # Приход раз в 3-5 дней
                if day_offset % 4 == 0:
                    sku = random.choice(list(products.keys()))
                    in_qty = random.randint(15, 60)
                    doc_num = f"ТТН-{random.randint(1000, 9999)}"
                    m = StockMovement.objects.create(
                        product=products[sku],
                        operation_type=StockMovement.OperationType.IN,
                        quantity=in_qty,
                        created_by=random.choice(users_pool),
                        document=doc_num,
                        note="Плановое оприходование партии товара"
                    )
                    # Корректируем created_at
                    StockMovement.objects.filter(pk=m.pk).update(created_at=day_time)
                    movements_created += 1

                # Расход почти каждый день (1-2 отгрузки в день)
                num_outs = random.choice([1, 1, 2])
                for _ in range(num_outs):
                    sku = random.choice(active_skus)
                    out_qty = random.randint(2, 18)
                    doc_num = f"Расходный ордер № {random.randint(100, 899)}"
                    m = StockMovement.objects.create(
                        product=products[sku],
                        operation_type=StockMovement.OperationType.OUT,
                        quantity=out_qty,
                        created_by=random.choice(users_pool),
                        document=doc_num,
                        note="Отгрузка в производственный отдел / клиенту"
                    )
                    StockMovement.objects.filter(pk=m.pk).update(created_at=day_time)
                    movements_created += 1

                # Редкие списания и перемещения
                if day_offset in [10, 24, 38, 49]:
                    sku = random.choice(active_skus)
                    m = StockMovement.objects.create(
                        product=products[sku],
                        operation_type=StockMovement.OperationType.WRITEOFF,
                        quantity=random.randint(1, 3),
                        created_by=admin_user,
                        document=f"Акт брака № {day_offset}",
                        note="Выбраковка при входном контроле"
                    )
                    StockMovement.objects.filter(pk=m.pk).update(created_at=day_time)
                    movements_created += 1

                if day_offset in [7, 21, 35, 52]:
                    sku = random.choice(active_skus)
                    m = StockMovement.objects.create(
                        product=products[sku],
                        operation_type=StockMovement.OperationType.TRANSFER,
                        quantity=random.randint(5, 12),
                        created_by=staff_user,
                        document=f"Накладная перемещения № {day_offset}",
                        note="Перемещение в зону комплектации"
                    )
                    StockMovement.objects.filter(pk=m.pk).update(created_at=day_time)
                    movements_created += 1

            self.stdout.write(f"Создано складских проводок: {movements_created}")

        self.stdout.write(self.style.SUCCESS(
            f"\nДемонстрационные данные успешно сгенерированы!\n"
            f"- Категорий: {len(categories)}\n"
            f"- Поставщиков: {len(suppliers)}\n"
            f"- Товаров: {len(products)}\n"
            f"- Заказов: {created_orders_count}\n"
            f"- Проводок (движений): {movements_created}\n\n"
            f"Тестовые учетные записи:\n"
            f"1) admin (роль: admin, пароль: Admin1234!)\n"
            f"2) manager (роль: manager, пароль: Manager1234!)\n"
            f"3) warehouse_staff (роль: warehouse_staff, пароль: Staff1234!)\n"
        ))
