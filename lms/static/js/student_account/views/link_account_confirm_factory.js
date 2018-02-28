(function(define) {
    'use strict';
    define('js/student_account/views/link_account_confirm_factory',
        [
            'jquery', 'underscore', 'backbone',
            'js/student_account/views/LinkAccountConfirmView',
            'js/student_account/models/user_account_model'
        ],
        function($, _, Backbone, LinkAccountConfirmView, UserAccountModel) {
            return function(disconnectUrl, userAccountsApiUrl, userData) {
                var view;
                var userAccountModel = new UserAccountModel({});
                userAccountModel.url = userAccountsApiUrl;

                view = new LinkAccountConfirmView({
                    userData: userData,
                    disconnectUrl: disconnectUrl,
                    model: userAccountModel
                });
                view.render();
            };
        }
    );
}).call(this, define || RequireJS.define);
