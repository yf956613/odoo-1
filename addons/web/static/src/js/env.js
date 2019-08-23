odoo.define("web.env", function(require) {
    "use strict";

    const core = require("web.core");
    const rpc = require("web.rpc");
    const session = require("web.session");

    const _t = core._t;

    /**
     * Sub QWeb class specialized for Odoo needs. This class handles two
     * additional concerns:
     * - only load new owl templates
     * - handle translations.
     *
     * Note that this class always translates sub templates.  It is not currently
     * suitable for some uses, such as using it in Kanban templates (which are
     * already translated by the server).
     *
     * To use untranslated templates, there are two strategies:
     * - either use owl.QWeb directly
     * - or, if you need it to be part of the main QWeb engine template system,
     *   then modify this class to add an extra parameter to addTemplates,
     *   and add a flag in the compilation context, and modify _compileNode to
     *   use that flag.
     */
    class OdooQWeb extends owl.QWeb {
        _addTemplate(name, elem) {
            if (elem.getAttribute("owl")) {
                elem.removeAttribute("owl");
                super._addTemplate(name, elem);
            }
        }
        _compileNode(elem, ctx) {
            switch (elem.nodeType) {
                case Node.TEXT_NODE:
                case Node.CDATA_SECTION_NODE:
                    // Text and CDATAs
                    const translation =
                        elem.parentNode.attributes["t-translation"];
                    if (translation && translation.value === "off") {
                        return;
                    }
                    const match = /^(\s*)([\s\S]+?)(\s*)$/.exec(elem.data);
                    if (match) {
                        elem.data = match[1] + _t(match[2]) + match[3];
                    }
                    break;
                case Node.ELEMENT_NODE:
                    // Element
                    for (let attr of ["label", "title", "alt", "placeholder"]) {
                        if (elem.attributes[attr]) {
                            elem.attributes[attr] = _t(elem.attributes[attr]);
                        }
                    }
            }

            return super._compileNode(elem, ctx);
        }
    }

    async function makeEnvironment() {
        const qweb = new OdooQWeb();
        await session.is_bound;
        qweb.addTemplates(session.templatesString);
        delete session.templatesString;

        function performRPC(params, options) {
            const query = rpc.buildQuery(params);
            return session.rpc(query.route, query.params, options);
        }

        return {
            qweb,

            _t: core._t,
            _lt: core._lt,
            bus: core.bus,
            rpc: performRPC,

            services: {}
        };
    }

    return makeEnvironment;
});
