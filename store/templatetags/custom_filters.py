# store/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def clp_format(value):
    try:
        value = int(round(float(value)))
        return f"CLP ${value:,}".replace(",", ".")
    except (ValueError, TypeError):
        return "CLP $0"
