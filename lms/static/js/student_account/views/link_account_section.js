(function(define, undefined) {
    'use strict';
    define([
        'gettext',
        'jquery',
        'underscore',
        'backbone',
        'text!templates/student_account/link_account.underscore'
    ], function(gettext, $, _, Backbone, sectionTemplate) {
        var LinkAccountSectionView = Backbone.View.extend({

            initialize: function(options) {
                this.options = options;
                _.bindAll(this, 'render', 'renderFields');
            },

            render: function() {
                this.$el.html(_.template(sectionTemplate)({
                    title: this.options.title,
                    subtitle: this.options.subtitle
                }));

                this.options.el.append(this.$el);

                this.renderFields();
            },

            renderFields: function() {
                var view = this,
                    sectionEl = $('.link-account-section-body');
                _.each(view.options.fields, function(field) {
                    sectionEl.append(field.view.render().el);
                });

                return this;
            }
        });

        return LinkAccountSectionView;
    });
}).call(this, define || RequireJS.define);
