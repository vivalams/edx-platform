(function(define) {
    'use strict';
    define([
        'jquery',
        'underscore',
        'backbone'
    ], function($, _, Backbone) {
        var LinkAccountConfirmView = Backbone.View.extend({
            el: '#link-account-confirm-main',
            events: {
                'click .link-account-disconnect': 'disconnect',
                'click .link-account-confirm': 'confirm'
            },
            initialize: function(options) {
                this.options = _.extend({}, options);
            },
            disconnect: function() {
                var data = {};

                // Disconnects the provider from the user's edX account.
                // See python-social-auth docs for more information.
                $.ajax({
                    type: 'POST',
                    url: this.options.disconnectUrl,
                    data: data,
                    dataType: 'html',
                    success: function() {
                        window.location.href = '/logout?msa_only=true';
                    },
                    error: function(error) {
                        console.error('Error Disconnecting User Account', error);
                    }
                });
            },
            confirm: function() {
                if (this.options.userData != null) {
                    var defaultOptions = {
                        contentType: 'application/merge-patch+json',
                        patch: true,
                        wait: true,
                        success: function(model, res) {
                            window.location.href = '/dashboard';
                        },
                        error: function(model, xhr) {
                            console.error('Error with Microsoft Account migration confirmation', model, xhr);
                        }
                    };
                    this.model.save(this.options.userData, defaultOptions);
                } else {
                    console.error('Error Updating User Account');
                }
            }
        });
        return LinkAccountConfirmView;
    });
}).call(this, define || RequireJS.define);
