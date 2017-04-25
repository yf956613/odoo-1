# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tests.common import TransactionCase
from odoo.tools import pycompat


class StockQuant(TransactionCase):
    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, order=None):
        domain = [
            ('product_id', '=', product_id.id),
            ('location_id', 'child_of', location_id.id),
        ]
        if lot_id:
            domain = expression.AND([[('lot_id', '=', lot_id.id)], domain])
        if package_id:
            domain = expression.AND([[('package_id', '=', package_id.id)], domain])
        if owner_id:
            domain = expression.AND([[('owner_id', '=', owner_id.id)], domain])
        return self.env['stock.quant'].search(domain, order=order)

    def test_get_available_quantity_1(self):
        """ Quantity availability with only one quant in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 1.0,
        })
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), 1.0)

    def test_get_available_quantity_2(self):
        """ Quantity availability with multiple quants in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        for i in range(3):
            self.env['stock.quant'].create({
                'product_id': product1.id,
                'location_id': stock_location.id,
                'quantity': 1.0,
            })
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), 3.0)

    def test_get_available_quantity_3(self):
        """ Quantity availability with multiple quants (including negatives ones) in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        for i in range(3):
            self.env['stock.quant'].create({
                'product_id': product1.id,
                'location_id': stock_location.id,
                'quantity': 1.0,
            })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': -3.0,
        })
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), 0.0)

    def test_get_available_quantity_4(self):
        """ Quantity availability with no quants in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), 0.0)

    def test_get_available_quantity_5(self):
        """ Quantity availability with multiple partially reserved quants in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 10.0,
            'reserved_quantity': 9.0,
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 1.0,
            'reserved_quantity': 1.0,
        })
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), 1.0)

    def test_get_available_quantity_6(self):
        """ Quantity availability with multiple partially reserved quants in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 10.0,
            'reserved_quantity': 20.0,
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 5.0,
            'reserved_quantity': 0.0,
        })
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), -5.0)

    def test_get_available_quantity_7(self):
        """ Quantity availability with only one tracked quant in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'tracking': 'lot',
        })
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': product1.id,
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 10.0,
            'reserved_quantity': 20.0,
            'lot_id': lot1.id,
        })
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location, lot_id=lot1), -10.0)

    def test_get_available_quantity_8(self):
        """ Quantity availability with a consumable product.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'consu',
        })
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), 0.0)
        self.assertEqual(len(self._gather(product1, stock_location)), 0)
        with self.assertRaises(ValidationError):
            self.env['stock.quant'].increase_available_quantity(product1, stock_location, 1.0)

    def test_increase_available_quantity_1(self):
        """ Increase the available quantity when no quants are already in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].increase_available_quantity(product1, stock_location, 1.0)
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), 1.0)

    def test_increase_available_quantity_2(self):
        """ Increase the available quantity when multiple quants are already in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        for i in range(2):
            self.env['stock.quant'].create({
                'product_id': product1.id,
                'location_id': stock_location.id,
                'quantity': 1.0,
            })
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), 2.0)
        self.env['stock.quant'].increase_available_quantity(product1, stock_location, 1.0)
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), 3.0)
        self.assertEqual(len(self._gather(product1, stock_location)), 2)

    def test_increase_available_quantity_3(self):
        """ Increase the available quantity when a concurrent transaction is already increasing
        the reserved quanntity for the same product.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product = self.env.ref('product.product_product_12')
        product.type = 'product'  # product 12 is a consumable by default
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product, stock_location), 10.0)

        # opens a new cursor and SELECT FOR UPDATE the quant, to simulate another concurrent reserved
        # quantity increase
        cr2 = self.registry.cursor()
        cr2.execute("SELECT id FROM stock_quant WHERE product_id=%s AND location_id=%s", (product.id, stock_location.id))
        quant_id = cr2.fetchone()
        cr2.execute("SELECT 1 FROM stock_quant WHERE id=%s FOR UPDATE", quant_id)

        self.env['stock.quant'].increase_available_quantity(product, stock_location, 1.0)
        cr2.rollback()
        cr2.close()
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product, stock_location), 11.0)
        self.assertEqual(len(self._gather(product, stock_location)), 2)

    def test_decrease_available_quantity_1(self):
        """ Decrease the available quantity when no quants are already in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].decrease_available_quantity(product1, stock_location, 1.0)
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), -1.0)

    def test_decrease_available_quantity_2(self):
        """ Decrease the available quantity when multiple quants are already in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        for i in range(2):
            self.env['stock.quant'].create({
                'product_id': product1.id,
                'location_id': stock_location.id,
                'quantity': 1.0,
            })
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), 2.0)
        self.assertEqual(len(self._gather(product1, stock_location)), 2)
        self.env['stock.quant'].decrease_available_quantity(product1, stock_location, 1.0)
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), 1.0)
        self.assertEqual(len(self._gather(product1, stock_location)), 2)

    def test_decrease_available_quantity_3(self):
        """ Decrease the available quantity when a concurrent transaction is already increasing
        the reserved quanntity for the same product.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product = self.env.ref('product.product_product_12')
        product.type = 'product'  # product 12 is a consumable by default
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product, stock_location), 10.0)
        quants = self._gather(product, stock_location)
        self.assertEqual(len(quants), 1)

        # opens a new cursor and SELECT FOR UPDATE the quant, to simulate another concurrent reserved
        # quantity increase
        cr2 = self.registry.cursor()
        cr2.execute("SELECT 1 FROM stock_quant WHERE id = %s FOR UPDATE", quants.ids)
        self.env['stock.quant'].decrease_available_quantity(product, stock_location, 1.0)
        cr2.rollback()
        cr2.close()
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product, stock_location), 9.0)
        self.assertEqual(len(self._gather(product, stock_location)), 2)

    def test_increase_reserved_quantity_1(self):
        """ Increase the reserved quantity of quantity x when there's a single quant in a given
        location which has an available quantity of x.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 10.0,
        })
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), 10.0)
        self.assertEqual(len(self._gather(product1, stock_location)), 1)
        self.env['stock.quant'].increase_reserved_quantity(product1, stock_location, 10.0)
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), 0.0)
        self.assertEqual(len(self._gather(product1, stock_location)), 1)

    def test_increase_reserved_quantity_2(self):
        """ Increase the reserved quantity of quantity x when there's two quants in a given
        location which have an available quantity of x together.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        for i in range(2):
            self.env['stock.quant'].create({
                'product_id': product1.id,
                'location_id': stock_location.id,
                'quantity': 5.0,
            })
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), 10.0)
        self.assertEqual(len(self._gather(product1, stock_location)), 2)
        self.env['stock.quant'].increase_reserved_quantity(product1, stock_location, 10.0)
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), 0.0)
        self.assertEqual(len(self._gather(product1, stock_location)), 2)

    def test_increase_reserved_quantity_3(self):
        """ Increase the reserved quantity of quantity x when there's multiple quants in a given
        location which have an available quantity of x together.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 5.0,
            'reserved_quantity': 2.0,
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 10.0,
            'reserved_quantity': 12.0,
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 8.0,
            'reserved_quantity': 3.0,
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 35.0,
            'reserved_quantity': 12.0,
        })
        # total quantity: 58
        # total reserved quantity: 29
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), 29.0)
        self.assertEqual(len(self._gather(product1, stock_location)), 4)
        self.env['stock.quant'].increase_reserved_quantity(product1, stock_location, 10.0)
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), 19.0)
        self.assertEqual(len(self._gather(product1, stock_location)), 4)

    def test_increase_reserved_quantity_4(self):
        """ Increase the reserved quantity of quantity x when there's multiple quants in a given
        location which have an available quantity of x together.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 5.0,
            'reserved_quantity': 7.0,
        })
        self.env['stock.quant'].create({
            'product_id': product1.id,
            'location_id': stock_location.id,
            'quantity': 10.0,
            'reserved_quantity': 10.0,
        })
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), -2.0)
        self.assertEqual(len(self._gather(product1, stock_location)), 2)
        self.env['stock.quant'].increase_reserved_quantity(product1, stock_location, 10.0)
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), -12.0)
        # a new quant was created as the max reservation was reached in the other one
        self.assertEqual(len(self._gather(product1, stock_location)), 3)

    def test_increase_reserved_quantity_5(self):
        """ Decrease the available quantity when no quant are in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].increase_reserved_quantity(product1, stock_location, 1.0)
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), -1.0)

    def test_increase_decrease_reserved_quantity_1(self):
        """ Decrease then increase reserved quantity when no quant are in a location.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.env['stock.quant'].increase_reserved_quantity(product1, stock_location, 1.0)
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), -1.0)
        self.env['stock.quant'].decrease_reserved_quantity(product1, stock_location, 1.0)
        self.assertEqual(self.env['stock.quant'].get_available_quantity(product1, stock_location), 0.0)
