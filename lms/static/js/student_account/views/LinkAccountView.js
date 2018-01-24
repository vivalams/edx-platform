(function(define) {
    'use strict';
    define([
        'gettext',
        'jquery',
        'underscore',
        'backbone',
        'js/views/fields',
        'text!templates/fields/field_social_link_account.underscore',
        'edx-ui-toolkit/js/utils/string-utils',
        'edx-ui-toolkit/js/utils/html-utils'
    ], function(
        gettext, $, _, Backbone,
        FieldViews,
        field_social_link_template,
        StringUtils,
        HtmlUtils
    ) {
        return FieldViews.LinkFieldView.extend({
            fieldTemplate: field_social_link_template,
            className: function() {
                return 'u-field u-field-social u-field-' + this.options.valueAttribute;
            },
            initialize: function(options) {
                this.options = _.extend({}, options);
                this._super(options);
                _.bindAll(this, 'redirect_to', 'inProgressMessage');
            },
            render: function() {
                var linkTitle = '',
                    linkClass = '',
                    subTitle = '',
                    screenReaderTitle = StringUtils.interpolate(
                            gettext('Sign in with {accountName}'),
                            {accountName: this.options.title}
                        );

                if (this.options.acceptsLogins) {
                      linkTitle = screenReaderTitle,
                      linkClass = 'social-field-unlinked';
                      subTitle = StringUtils.interpolate(
                          gettext('Link your {accountName} account to your {platformName} account and use {accountName} to sign in to {platformName}.'),  // eslint-disable-line max-len
                            {accountName: this.options.title, platformName: this.options.platformName}
                      );
                }

                HtmlUtils.setHtml(this.$el, HtmlUtils.template(this.fieldTemplate)({
                    id: this.options.valueAttribute,
                    title: this.options.title,
                    screenReaderTitle: screenReaderTitle,
                    linkTitle: linkTitle,
                    subTitle: subTitle,
                    linkClass: linkClass,
                    linkHref: '#',
                    message: this.helpMessage
                }));
                this.delegateEvents();
                return this;
            },
            linkClicked: function(event) {
                event.preventDefault();

                this.showInProgressMessage();
                // Direct the user to the providers site to start the authentication process.
                // See python-social-auth docs for more information.
                this.redirect_to(this.options.connectUrl);
            },
            redirect_to: function(url) {
                window.location.href = url;
            },
            inProgressMessage: function() {
                return HtmlUtils.joinHtml(this.indicators.inProgress, (
                    this.options.connected ? gettext('Unlinking') : gettext('Linking')
                ));
            }
        });
    });
}).call(this, define || RequireJS.define);
