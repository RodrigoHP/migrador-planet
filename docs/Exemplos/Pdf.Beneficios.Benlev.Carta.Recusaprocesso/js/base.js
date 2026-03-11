ko.bindingHandlers.number = {
    update: function (element, valueAccessor, allBindingsAccessor) {
        var value = ko.unwrap(valueAccessor());
        if (typeof value === 'number' && isFinite(value)) {
            var precision = ko.utils.unwrapObservable(allBindingsAccessor().precision) ||
                ko.bindingHandlers.number.defaultPrecision;
            value = value.toFixed(precision).replace('.', ',').replace(/(\d)(?=(\d{3})+(?!\d))/g, "$1.");
            ko.bindingHandlers.text.update(element, function () { return value; });
        } else
            ko.bindingHandlers.text.update(element, function () { return "—" });
    },
    defaultPrecision: 2
};

ko.applyBindings(ko.mapping.fromJS(data));