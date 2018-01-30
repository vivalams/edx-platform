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
                        window.location.href = '/logout';
                    },
                    error: function(xhr) {
                        console.error('Error Disconnecting User Account')
                    }
                });
            },
            confirm: function() {
                var data = {
                    'email': this.options.newEmail,
                    'name': this.options.newFullName,
                    'force_email_update': true
                };

                var view = this;

                var defaultOptions = {
                    contentType: 'application/merge-patch+json',
                    patch: true,
                    wait: true,
                    // data: JSON.stringify(_.extend(data, this.model.attributes)),
                    success: function(model, res) {
                        model.unset('force_email_update', {silent: true});
                        window.location.href = '/dashboard';
                    },
                    error: function(model, xhr) {
                        view.disconnect();
                    }
                };
                this.model.save(data, defaultOptions);
            }
        });
        return LinkAccountConfirmView;
    });
}).call(this, define || RequireJS.define);
