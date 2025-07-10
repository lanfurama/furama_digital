# app/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    try:
        return dictionary.get(key)
    except (AttributeError, TypeError):
        return None

@register.filter
def index(sequence, position):
    try:
        return sequence[position]
    except:
        return ''