odoo.define('qwarie.custom_survey', function (require) {
            'use strict';
            var Model = require('web.Model');
            var SurveyModel = new Model('survey.user_input');
            var ajax = require('web.ajax');

            var pathname = window.location.pathname;
            var path = pathname.split('/');
            var userToken = path[path.length - 1];
            if (userToken.length < 10) {
                return $.Deferred().reject("Incorrect User Token");
            }
            $(document).ready(function() {
                    if (pathname.indexOf('/survey/') > -1 || pathname.indexOf('/exam') > -1 || pathname.indexOf('/feedback') > -1) {
                        $('#top_menu').hide();
                        $('#footer div.row:first').hide();
                    }
                    if (pathname.indexOf('/survey/start/') > -1 || pathname.indexOf('/survey/print/') > -1 ||
                        pathname.indexOf('/exam/start/') > -1 || pathname.indexOf('/exam/print/') > -1 ||
                        pathname.indexOf('/feedback/start/') > -1 || pathname.indexOf('/feedback/print/') > -1) {
                        ajax.jsonRpc('/survey/get_user_results', 'call', {
                            'user_token': userToken,
                        }).then(function(result) {
                                if (result) {
                                    if (result.is_quizz && (pathname.indexOf('/survey/print/') > -1 || pathname.indexOf('/exam/print/') > -1)) {
                                        if ('weighted_average' in result) {
                                            var values1 = ['0%', '1%', '2%', '3%', '4%', '5%', '6%', '7%', '8%', '9%']
                                            if ((values1.indexOf(result.weighted_average) === -1) && (result.weighted_average >= '70%') || (result.weighted_average == '100%')) {
                                                $('.jumbotron:first h1:first').after('<div id="total_quiz_mark" class="quiz-mark-green">Total: ' + result.total_score + ' points out of ' + result.max_total_score +'('+result.weighted_average+')</div>');
                                            } else if ((result.weighted_average < '70%') || (values1.indexOf(result.weighted_average) != -1)) {
                                                $('.jumbotron:first h1:first').after('<div id="total_quiz_mark" class="quiz-mark-red">Total: ' + result.total_score + ' points out of ' + result.max_total_score +'('+result.weighted_average+')</div>');
                                            }
                                        } else if (result.max_total_score < 100) {
                                            var score_percentage = ((result.total_score*100)/result.max_total_score).toFixed(2) || 0;
                                            if (score_percentage >= 70){
                                                $('.jumbotron:first h1:first').after('<div id="total_quiz_mark" class="quiz-mark-green">Total: ' +
                                                result.total_score + ' points out of ' + result.max_total_score + ' ('+parseInt(score_percentage)+'%)</div>');
                                            } else{
                                            $('.jumbotron:first h1:first').after('<div id="total_quiz_mark" class="quiz-mark-red">Total: ' +
                                                result.total_score + ' points out of ' + result.max_total_score + ' ('+parseInt(score_percentage)+'%)</div>');
                                            }
                                        } else {
                                        $('.jumbotron:first h1:first').after('<div id="total_quiz_mark" class="quiz-mark-red">Total: ' + result.total_score + ' points out of ' + result.max_total_score +'</div>');
                                        }
                                        $('#total_quiz_mark').after('<span class="level_scores"/>');
                                        if ('l1_score' in result) {
                                            $('.level_scores').append('<span class="l1_scores">Level 1: '+result.l1_score+'</span><br/>');
                                        }
                                        if ('l2_score' in result) {
                                            $('.level_scores').append('<span class="l2_scores">Level 2: '+result.l2_score+'</span><br/>');
                                        }
                                        _.each(result.scores, function(value, key){
                                            if (value.score) {
                                                if (value.answer_type === 'multiple_choice') {
                                                    value.score = value.score * value.multiple_score
                                                    if (value.score < value.max_score) {
                                                        if (value.type === 'suggestion') {
                                                            $('span[data-score-question="' + key + '"]').closest('h2').append('<br/><span class="quiz-mark-red">' + value.score + (value.score == 0 || value.score > 1 ? ' points' : ' point') + ' out of ' + value.max_score + '</span>');
                                                        }
                                                    } else if (value.score == 0) {
                                                        if (value.type === 'suggestion') {
                                                            $('span[data-score-question="' + key + '"]').closest('h2').append('<br/><span class="quiz-mark-red">' + '0 points out of ' + value.max_score + '</span>');
                                                        }
                                                    } else {
                                                        if (value.type === 'suggestion') {
                                                            $('span[data-score-question="' + key + '"]').closest('h2').append('<br/><span class="quiz-mark-green">' + value.score + (value.score == 0 || value.score > 1 ? ' points' : ' point') + ' out of ' + value.max_score + '</span>');
                                                        }
                                                    }
                                                } if (value.answer_type === 'simple_choice') {
                                                    if (value.score < value.max_score) {
                                                        if (value.type === 'suggestion') {
                                                            $('span[data-score-question="' + key + '"]').closest('h2').append('<br/><span class="quiz-mark-red">' + value.score + (value.score == 0 || value.score > 1 ? ' points' : ' point') + ' out of ' + value.max_score + '</span>');
                                                        }
                                                    } else {
                                                        if (value.type === 'suggestion') {
                                                            $('span[data-score-question="'+key+'"]').closest('h2').append('<br/><span class="quiz-mark-green">' + value.score + (value.score == 0 || value.score > 1 ? ' points' : ' point') + ' out of ' + value.max_score + '</span>');
                                                        }
                                                    }
                                                }
                                            } else {
                                                if (value.type === 'suggestion') {
                                                    $('span[data-score-question="' + key + '"]').closest('h2').append('<br/><span class="quiz-mark-red">' + '0 points out of ' + value.max_score + '</span>');
                                                }
                                            }
                                        });
                                        if (result.event_name) {
                                            var courseInfo = '<br/><div align="left">';
                                            courseInfo += '<p><b>Course:</b></p><p>'+result.event_name+'</p>';
                                            courseInfo += '<p><b>Dates:</b></p><p>'+result.event_date_start+' to '+result.event_date_end+'</p>';
                                            courseInfo += '<p><b>Trainer:</b></p><p>'+result.event_trainer+'</p>';
                                            if (result.event_assistant !== null) {
                                                courseInfo += '<p><b>Assistant Trainer:</b></p><p>'+result.event_assistant+'</p>';
                                            }
                                            courseInfo += '<p><b>Delegate Name:</b></p><p>'+result.user_name+'</p>';
                                            courseInfo += '<p><b>Delegate Email:</b></p><p>'+result.user_email+'</p>';
                                            courseInfo += '</div>';
                                            $('.jumbotron:first h1:first').first().after(courseInfo);
                                        }
                                    }
                                }    
                            });
                        }
                        var countdown = document.getElementById('countdown');
                        if (countdown) {
                            if (pathname.indexOf('/survey/fill/') > -1 ||
                                pathname.indexOf('/exam/fill/') > -1 ||
                                pathname.indexOf('/feedback/fill/') > -1) {
                                ajax.jsonRpc('/survey/get_user_test_time', 'call', {
                                    'user_token': userToken,
                                }).then(function (result) {
                                    if (result) {
                                        var start_exam = moment(result.start_exam + "Z").local();
                                        var duration = parseInt(result.duration);
                                        if (isNaN(duration)){
                                            return;
                                        }
                                        var end_exam = start_exam.add(duration, "m");
                                        var dateNow = moment()
                                        var seconds = end_exam.diff(dateNow, "seconds");
                                        var countdownTimer = setInterval(function () {
                                            var minutes = Math.round((seconds - 30) / 60);
                                            var remainingSeconds = seconds % 60;
                                            if (remainingSeconds < 10) {
                                                remainingSeconds = "0" + remainingSeconds;
                                            }
                                            countdown.innerHTML = "Total Duration" + " " + minutes + ":" + remainingSeconds;
                                            if (seconds <= 0) {
                                                clearInterval(countdownTimer);
                                                ajax.jsonRpc('/survey/set_survey_complete', 'call', {
                                                    'user_token': userToken,
                                                }).then(function (result) {
                                                    $('.btn-primary[value="next"], .btn-primary[value="finish"]').click();
                                                })
                                            } else {
                                                seconds--;
                                            }
                                        }, 1000);
                                    }
                                })
                            }
                        }
                    });


                var backPressed = false;
                if (window.history && window.history.pushState) {
                    window.history.pushState('forward', null, '#forward');

                    $(window).on('popstate', function (e) {
                        e.preventDefault();
                        if (!backPressed) {
                            var path = pathname.split('/');
                            var userToken = path[path.length - 1];
                            ajax.jsonRpc('/survey/user_back_pressed', 'call', {
                                'user_token': userToken,
                            });
                            backPressed = true;
                        }

                        window.history.pushState('forward', null, '#forward');
                    });
                }
            });