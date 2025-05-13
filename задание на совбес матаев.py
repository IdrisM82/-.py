from django.db import models
from django.contrib import admin
from django import template
from django.urls import reverse
from django.apps import AppConfig


class MenuItem(models.Model):
    title = models.CharField(max_length=200)
    url = models.CharField(max_length=200, blank=True)
    named_url = models.CharField(max_length=200, blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.CASCADE)
    menu_name = models.CharField(max_length=100)

    def __str__(self):
        return self.title


class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'parent', 'menu_name')
    list_filter = ('menu_name',)
    search_fields = ('title',)

admin.site.register(MenuItem, MenuItemAdmin)


class MenuConfig(AppConfig):
    name = 'menu'


register = template.Library()

def build_menu(menu_items, active_url):
    menu_dict = {item.id: item for item in menu_items}
    tree = []

    for item in menu_items:
        if item.parent is None:
            tree.append(item)

    def add_children(parent):
        children = [item for item in menu_items if item.parent == parent]
        for child in children:
            child.children = add_children(child)
        return children

    for item in tree:
        item.children = add_children(item)

    return tree

@register.inclusion_tag('menu/menu.html')
def render_menu(menu_name, active_url):
    menu_items = MenuItem.objects.filter(menu_name=menu_name)
    menu_tree = build_menu(menu_items, active_url)
    return {'menu_tree': menu_tree, 'active_url': active_url}


template_code = """
<ul>
    {% for item in menu_tree %}
        <li class="{% if item.url == active_url or item.named_url == active_url %}active{% endif %}">
            <a href="{% if item.url %}{{ item.url }}{% elif item.named_url %}{% url item.named_url %}{% endif %}">{{ item.title }}</a>
            {% if item.children %}
                <ul>
                    {% for child in item.children %}
                        <li class="{% if child.url == active_url or child.named_url == active_url %}active{% endif %}">
                            <a href="{% if child.url %}{{ child.url }}{% elif child.named_url %}{% url child.named_url %}{% endif %}">{{ child.title }}</a>
                        </li>
                    {% endfor %}
                </ul>
            {% endif %}
        </li>
    {% endfor %}
</ul>
"""


with open('menu/templates/menu/menu.html', 'w') as f:
    f.write(template_code)