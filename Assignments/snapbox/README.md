# SnapBox — سامانه مدیریت سفارش با OOP

## اجرا
```bash
python main.py < input.txt
```
ورودی و خروجی دقیقاً مطابق [صورت کوئرا](https://quera.org/problemset/106799) است (مثلاً `ADD-DRIVER Ali (10, 10) VAN`، `ORDER-UPDATE PICKUP Ali 1`). هر دو نمونه کوئرا در `tests/samples/` و `tests/test_main.py` به‌صورت تست خودکار ثبت شده‌اند.

## معماری
| فایل | مسئولیت |
|---|---|
| `driver.py` | `Driver`: اطلاعات و وضعیت یک راننده (Propertyهای فقط‌خواندنی) |
| `order.py` | `Order`: اطلاعات و وضعیت یک سفارش + توابع اعتبارسنجی مشترک (`TypeError`/`ValueError`) |
| `delivery_system.py` | `DeliverySystem`: تمام منطق کسب‌وکار (تخصیص، چرخه وضعیت، پرداخت، جست‌وجو) |
| `main.py` | فقط تجزیه ورودی و قالب‌بندی خروجی؛ بدون منطق کسب‌وکار |

داده‌ها با پیشوند `_` ذخیره می‌شوند و تغییر آن‌ها فقط با متدهای داخلی (`_take`, `_release`, ...) توسط `DeliverySystem` انجام می‌شود. ترتیب ثبت با `dict` حفظ می‌شود.

## تست
```bash
python -m unittest test_contract -v
python -m unittest discover -s tests -v
```

## قابلیت خلاقانه: انعام (`add_tip`)
`DeliverySystem.add_tip(order_id: int, amount: Decimal) -> bool`
- فقط برای سفارش `DELIVERED`؛ ۱۰۰٪ انعام به اعتبار راننده می‌رود (سهم شرکت صفر).
- `Order.tip` مجموع انعام‌های سفارش را نشان می‌دهد (فقط‌خواندنی).
- `False`: سفارش ناموجود، غیر `DELIVERED`، یا مجموع انعام بیش از `cost` سفارش.
- `TypeError` اگر `amount` از نوع `Decimal` نباشد؛ `ValueError` اگر مثبت نباشد.
- تست‌ها: `tests/test_extension.py` (۳ تست).

## استفاده از AI
بخش مهمی از کد و تست‌های اولیه با کمک Claude تولید شد.
