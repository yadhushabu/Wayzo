# wayzo/templatetags/custom_filters.py
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

@register.filter(name='divisibleby')
def divisibleby(value, arg):
    """Check if value is divisible by arg"""
    try:
        return int(float(value)) % int(float(arg)) == 0
    except (ValueError, TypeError):
        return False

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    try:
        return dictionary.get(key)
    except (AttributeError, TypeError):
        return None

@register.filter(name='range')
def range_filter(value):
    """Generate a range of numbers"""
    try:
        return range(int(value))
    except (ValueError, TypeError):
        return range(0)

@register.filter(name='get_attr')
def get_attr(obj, attr):
    """Get attribute from object by name"""
    try:
        return getattr(obj, attr, None)
    except (AttributeError, TypeError):
        return None

@register.filter(name='list_length')
def list_length(value):
    """Get length of a list"""
    try:
        return len(value)
    except (TypeError):
        return 0

@register.simple_tag
def update_variable(value):
    """Update a variable value"""
    return value

@register.filter
def truncatewords_after_first(value, count):
    words = value.split()
    return " ".join(words[int(count):])

@register.filter(name='split')
def split(value, delimiter):
    """
    Split a string into a list
    """
    try:
        return value.split(delimiter)
    except AttributeError:
        return []
    
from travellers.models import Follow

@register.filter(name='check_following')
def check_following(user, target_user):
    if not user or not user.is_authenticated:
        return False

    return Follow.objects.filter(
        follower=user,
        following=target_user
    ).exists()

from django import template

register = template.Library()

@register.filter
def replace_underscore(value):
    """Replace underscores with spaces and then title case"""
    if value:
        return value.replace('_', ' ').title()
    return value

@register.filter
def format_action(value):
    """Format action strings nicely"""
    if value:
        # Replace underscores with spaces
        formatted = value.replace('_', ' ')
        # Replace specific patterns
        formatted = formatted.replace('created', 'Created')
        formatted = formatted.replace('updated', 'Updated')
        formatted = formatted.replace('deleted', 'Deleted')
        formatted = formatted.replace('booked', 'Booked')
        formatted = formatted.replace('payment', 'Payment')
        formatted = formatted.replace('success', 'Success')
        formatted = formatted.replace('failed', 'Failed')
        return formatted
    return value

from django import template

register = template.Library()

@register.filter(name='replace')
def replace(value, arg):
    """Replace a string with another string.
    Usage: {{ value|replace:"old|new" }}
    """
    if not value:
        return value
    try:
        old, new = arg.split('|')
        return value.replace(old, new)
    except (ValueError, AttributeError):
        return value

@register.filter(name='selectattr')
def selectattr(iterable, args):
    """Filter a list by attribute.
    Usage: {{ list|selectattr:"status,equalto,available" }}
    """
    try:
        attr_name, operator, value = args.split(',')
        if operator == 'equalto':
            return [item for item in iterable if getattr(item, attr_name, None) == value]
        elif operator == 'notequalto':
            return [item for item in iterable if getattr(item, attr_name, None) != value]
        else:
            return iterable
    except (ValueError, AttributeError):
        return iterable