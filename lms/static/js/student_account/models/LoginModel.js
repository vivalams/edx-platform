(function(define) {
    'use strict';
    define([
        'jquery',
        'backbone',
        'jquery.url'
    ], function($, Backbone) {
        return Backbone.Model.extend({
            defaults: {
                email: '',
                password: '',
                remember: false
            },

            ajaxType: '',
            urlRoot: '',
            msaMigrationEnabled: false,
            msa_migration_pipeline_status: null,

            initialize: function(attributes, options) {
                this.ajaxType = options.method;
                this.urlRoot = options.url;
                this.msaMigrationEnabled = options.msaMigrationEnabled;
                this.msa_migration_pipeline_status = options.msa_migration_pipeline_status;
            },

            sync: function(method, model) {
                var headers = {'X-CSRFToken': $.cookie('csrftoken')},
                    data = {},
                    analytics,
                    courseId = $.url('?course_id');

                // If there is a course ID in the query string param,
                // send that to the server as well so it can be included
                // in analytics events.
                if (courseId) {
                    analytics = JSON.stringify({
                        enroll_course_id: decodeURIComponent(courseId)
                    });
                }
                // Include all form fields and analytics info in the data sent to the server
                $.extend(data, model.attributes, {analytics: analytics});

                if (this.msaMigrationEnabled) {
                    var msaAttributes = {};
                    if (!data.hasOwnProperty('msa_migration_pipeline_status')) {
                        msaAttributes['msa_migration_pipeline_status'] = this.msa_migration_pipeline_status || 'email_lookup'
                    }
                    if (!data['password']) {
                        msaAttributes['password'] = 'msa_email_lookup'
                    }

                    $.extend(data, msaAttributes);
                    this.msa_migration_pipeline_status = data['msa_migration_pipeline_status']
                }
                $.ajax({
                    url: model.urlRoot,
                    type: model.ajaxType,
                    data: data,
                    headers: headers,
                    success: function(json) {
                        if (model.msaMigrationEnabled) {
                            if (json.hasOwnProperty('value')) {
                                data['msa_migration_pipeline_status'] = json['value']
                                model.msa_migration_pipeline_status = json['value']
                            }
                            if (data['msa_migration_pipeline_status'] === 'login_not_migrated' && data['password'] !== 'msa_email_lookup') {
                                data['msa_migration_pipeline_status'] = ''
                            }
                        }
                        model.trigger('sync', data);
                    },
                    error: function(error) {
                        console.log('ERROR HERE: ', error)
                        model.trigger('error', error);
                    }
                })
            }
        });
    });
}).call(this, define || RequireJS.define);
