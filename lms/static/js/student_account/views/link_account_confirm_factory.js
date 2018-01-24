(function(define) {
    'use strict';
    define('js/student_account/views/link_account_confirm_factory',
        ['jquery', 'underscore', 'backbone', 'js/student_account/views/LinkAccountConfirmView', 'utility'],
        function($, _, Backbone, LinkAccountConfirmView) {
            return function(disConnectUrl) {
                var view = new LinkAccountConfirmView({disConnectUrl: disConnectUrl});
                view.render();
            };
        }
    );
}).call(this, define || RequireJS.define);
