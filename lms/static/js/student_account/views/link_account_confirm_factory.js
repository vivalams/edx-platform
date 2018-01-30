(function(define) {
    'use strict';
    define('js/student_account/views/link_account_confirm_factory',
        ['jquery', 'underscore', 'backbone',
            'js/student_account/views/LinkAccountConfirmView',
            'js/student_account/models/user_account_model'
        ],
        function($, _, Backbone, LinkAccountConfirmView, UserAccountModel) {
            return function(newEmail, newFullName, disconnectUrl, userAccountsApiUrl) {
                var userAccountModel = new UserAccountModel({});
                userAccountModel = new UserAccountModel();
                userAccountModel.url = userAccountsApiUrl;

                var view = new LinkAccountConfirmView({
                    newEmail: newEmail,
                    newFullName: newFullName,
                    disconnectUrl: disconnectUrl,
                    userAccountsApiUrl: userAccountsApiUrl,
                    model: userAccountModel
                });
                view.render();
            };
        }
    );
}).call(this, define || RequireJS.define);
