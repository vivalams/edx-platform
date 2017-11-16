(function(define) {
    'use strict';
    define([
        'gettext', 'jquery', 'underscore', 'backbone',
        'js/student_account/views/LinkAccountView',
        'js/student_account/views/link_account_section',
        'edx-ui-toolkit/js/utils/string-utils'
    ], function(gettext, $, _, Backbone, LinkAccountView, LinkAccountSectionView, StringUtils) {
        return function(
            authData,
            platformName
        ) {
            var linkAccountElement, linkAccountSection, linkAccountSectionView,
                showLoadingError;

            linkAccountElement = $('.wrapper-linkaccount-settings');
            linkAccountSection = {
                el: linkAccountElement,
                title: gettext('Linked Accounts'),
                subtitle: StringUtils.interpolate(
                    gettext('You can link your social media accounts to simplify signing in to {platform_name}.'),
                    {platform_name: platformName}
                ),
                fields: _.map(authData.providers, function(provider) {
                    return {
                        'view': new LinkAccountView({
                            title: provider.name,
                            valueAttribute: 'auth-' + provider.id,
                            helpMessage: '',
                            connected: provider.connected,
                            connectUrl: provider.connect_url,
                            acceptsLogins: provider.accepts_logins,
                            disconnectUrl: provider.disconnect_url,
                            platformName: platformName
                        })
                    };
                })
            };

            linkAccountSectionView = new LinkAccountSectionView(linkAccountSection);

            linkAccountSectionView.render();
            return {
                linkAccountSectionView: linkAccountSectionView
            };
         };
    });
}).call(this, define || RequireJS.define);
