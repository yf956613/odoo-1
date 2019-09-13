odoo.define("point_of_sale.ProductListWidget", function(require) {
    "use strict";

    const Product = require("point_of_sale.Product");

    class ProductListWidget extends owl.Component {
        selectProduct() {
            return this.props.onSelectProduct(...arguments);
        }
    }
    ProductListWidget.components = { Product };
    ProductListWidget.props = ["products", "pricelist", "unitsByUOM", "onSelectProduct"];

    return ProductListWidget;
});
