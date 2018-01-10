(function(define, undefined) {
    'use strict';
    define([
        'jquery',
        'underscore',
        'backbone',
        'gettext'
    ], function($, _, Backbone, gettext) {
        var LinkAccountConfirmView = Backbone.View.extend({
            el: "#link-account-confirm-main",
            events: {
                "click .link-account-disconnect": "disconnect",
            },
            initialize: function(options) {
                this.options = _.extend({}, options);
            },
            disconnect: function() {
                var data = {};

                // Disconnects the provider from the user's edX account.
                // See python-social-auth docs for more information.
                var view = this;
                $.ajax({
                    type: 'POST',
                    url: this.options.disConnectUrl,
                    data: data,
                    dataType: 'html',
                    success: function() {
                        window.location.href = '/logout';
                    },
                    error: function(xhr) {
                        view.showErrorMessage(xhr);
                    }
                });
            }
        });
        return LinkAccountConfirmView;
    });
}).call(this, define || RequireJS.define);

