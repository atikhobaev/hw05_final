from django import template

register = template.Library()


@register.filter
def uglify(field: str):
    source = field
    result = ""
    for index, value in enumerate(source):
        if index % 2:
            result += value.upper()
        else:
            result += value.lower()
    return result
