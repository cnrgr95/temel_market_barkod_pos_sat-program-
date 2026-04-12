import sys, os
sys.path.insert(0, os.path.abspath('.'))
class MockDB:
    def get_setting(self, *args): return '[]'
    def list_categories(self, *args): return []
    def list_products(self, *args): return []
from flet_pos.pages.products_page import ProductsPage
pp = ProductsPage(MockDB(), '.', lambda: None)
print('ProductsPage SUCCESS')
