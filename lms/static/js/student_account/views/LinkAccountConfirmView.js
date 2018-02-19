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
                "click .link-account-confirm": "confirm"
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
                    url: this.options.disconnectUrl,
                    data: data,
                    dataType: 'html',
                    success: function() {
                        window.location.href = '/logout?redirect_login=true';
                    },
                    error: function(error, param) {
                        console.error(error)
                        console.log(param)
                        console.error('Error Disconnecting User Account', error)
                    }
                });
            },
            confirm: function() {
                if (this.options.userData != null) {
                    var view = this;
                    var defaultOptions = {
                        contentType: 'application/merge-patch+json',
                        patch: true,
                        wait: true,
                        success: function(model, res) {
                            window.location.href = '/dashboard';
                        },
                        error: function(model, xhr) {
                            window.location.href = '/dashboard';
                        }
                    };
                    this.model.save(this.options.userData, defaultOptions);
                } else {
                    console.error("Error Updating User Account")
                }
            }
        });
        return LinkAccountConfirmView;
    });
}).call(this, define || RequireJS.define);
