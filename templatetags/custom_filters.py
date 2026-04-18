from django import template
from decimal import Decimal

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='divide')
def divide(value, arg):
    """Divide the value by the argument"""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter(name='subtract')
def subtract(value, arg):
    """Subtract arg from value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='add')
def add(value, arg):
    """Add arg to value"""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='percentage')
def percentage(value, arg):
    """Calculate arg% of value"""
    try:
        return (float(value) * float(arg)) / 100
    except (ValueError, TypeError):
        return 0

@register.filter(name='currency')
def currency(value):
    """Format as Indian currency"""
    try:
        value = float(value)
        return f"₹{value:,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"

@register.filter(name='floatformat')
def floatformat(value, arg=-1):
    """Custom floatformat filter"""
    try:
        value = float(value)
        if arg == -1:
            return f"{value:,.2f}"
        else:
            return f"{value:,.{int(arg)}f}"
    except (ValueError, TypeError):
        return value