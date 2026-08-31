"""Realistic demo CSV payloads for bookkeeper demos."""


def get_demo_shopify_csv() -> bytes:
    return (
        "Name,Email,Financial Status,Total,Taxes,Shipping\n"
        "#1042,sarah@oakridgehome.com,paid,189.50,12.40,8.00\n"
        "#1043,mike@brightlineco.com,paid,74.25,4.85,5.00\n"
        "#1044,ops@northwindgoods.com,paid,312.00,20.28,0.00\n"
        "#1045,jen@harborviewstudio.com,paid,56.90,3.70,5.00\n"
        "#1046,ap@crestfieldsupply.com,paid,428.75,27.87,12.00\n"
        "#1047,hello@urbanpetco.com,paid,98.40,6.40,6.50\n"
    ).encode("utf-8")


def get_demo_stripe_csv() -> bytes:
    return (
        "Created (UTC),Description,Gross,Fee,Net,Currency\n"
        "2026-08-01 14:22:10,Shopify order #1042,189.50,5.80,183.70,usd\n"
        "2026-08-01 15:01:44,Shopify order #1043,74.25,2.45,71.80,usd\n"
        "2026-08-01 16:18:02,Shopify order #1044,312.00,9.35,302.65,usd\n"
        "2026-08-01 17:05:33,Shopify order #1045,56.90,1.95,54.95,usd\n"
        "2026-08-01 18:40:19,Shopify order #1046,428.75,12.73,416.02,usd\n"
        "2026-08-02 09:12:55,Shopify order #1047,98.40,3.15,95.25,usd\n"
    ).encode("utf-8")
