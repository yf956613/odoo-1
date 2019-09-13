odoo.define("point_of_sale.UsernameWidget", function(require) {
    "use strict";

    const AbstractPosConnectedComponent = require("point_of_sale.BackboneStore");

    class UsernameWidget extends AbstractPosConnectedComponent {}
    UsernameWidget.mapStoreToProps = function (model) {
        const { name } = model.get_cashier();
        return {
            name,
        };
    };
    UsernameWidget.props = ["name"];
    UsernameWidget.defaultProps = {
        name: "unknown",
    };

    return UsernameWidget;
});
