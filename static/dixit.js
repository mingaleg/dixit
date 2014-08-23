var nickname = '';
var cards = [];
var choosing = false;
var master = false;
var stage = 'break';
var round_master = '';
var is_round_master = false;
var valid_choose = false;
var cur_choose = '';
var choosers = {};
var lastcardclick = {};

window.onload = function() {

    $('body').append('<div id="blackout"></div>'); 
    var boxWidth = 400;

    $('.viewport_inner').hover(function(evt){
        if (choosing && valid_choose) $('.selector')[0].style.display = 'block';
    }, function(evt){
        $('.selector')[0].style.display = 'none';
    });

    function centerBox() {
         
        /* определяем нужные данные */
        var winWidth = $(window).width();
        var winHeight = $(document).height();
        var scrollPos = $(window).scrollTop();
         
        /* Вычисляем позицию */
         
        var disWidth = (winWidth - boxWidth) / 2
        var disHeight = scrollPos + 150;
         
        /* Добавляем стили к блокам */
        $('.popup-box').css({'width' : boxWidth+'px', 'left' : disWidth+'px', 'top' : disHeight+'px'});
        $('#blackout').css({'width' : winWidth+'px', 'height' : winHeight+'px'});
         
        return false;       
    }

    $(window).resize(centerBox);
    $(window).scroll(centerBox);
    centerBox();

    function UpdatePopupLinks() {
        $('[class*=popup-link]').click(function(e) {

            /* Предотвращаем действия по умолчанию */
            e.preventDefault();
            e.stopPropagation();

            /* Получаем id (последний номер в имени класса ссылки) */
            var name = $(this).attr('class').split('-');
            var id = name[name.length - 1];
            var scrollPos = $(window).scrollTop();

            /* Корректный вывод popup окна, накрытие тенью, предотвращение скроллинга */
            $('#popup-box-'+id).show();
            $('#blackout').show();
            $('html,body').css('overflow', 'hidden');

            /* Убираем баг в Firefox */
            $('html').scrollTop(scrollPos);
        });
    };

    UpdatePopupLinks();

    $('#login_link').click(function(evt) {
        $('#nick')[0].focus();
    });

    $('[class*=popup-box]').click(function(e) { 
        /* Предотвращаем работу ссылки, если она являеться нашим popup окном */
        e.stopPropagation(); 
    });
    $('html').click(function() { 
        var scrollPos = $(window).scrollTop();
        /* Скрыть окно, когда кликаем вне его области */
        $('[id^=popup-box-]').hide(); 
        $('#blackout').hide(); 
        $("html,body").css("overflow","auto");
        $('html').scrollTop(scrollPos);
    });
    $('.close').click(function() { 
        var scrollPos = $(window).scrollTop();
        /* Скрываем тень и окно, когда пользователь кликнул по X */
        $('[id^=popup-box-]').hide(); 
        $('#blackout').hide(); 
        $("html,body").css("overflow","auto");
        $('html').scrollTop(scrollPos);
    });


    var s = new io.connect(window.location.hostname, {
        port: 8001,
        rememberTransport: false,
        transports: [
            'websocket',
            'flashsocket',
            'xhr-multipart',
            'xhr-polling'
        ]
    });

    s.emit('update_scoreboard');

    $(window).unload(Sfunction() {
        s.close();
    });

    //s.connect();

    s.on('message', function(data) {
        $("#log_inner").append("<div>" + data + "</div>");
        $('#log_inner').scrollTop($('#log_inner').height())
    });
    s.on('system', function(data) {
        $("#log_inner").append("<div class='system'>" + data + "</div>");
        $('#log_inner').scrollTop($('#log_inner').height())
    });
    s.on('error', function(data) {
        $("#log_inner").append("<div class='error'>" + data['comment'] + "</div>");
        $('#log_inner').scrollTop($('#log_inner').height())
    });
    s.on('results', function(data) {
        $("#log_inner").append("<div class='results'>" + data + "</div>");
        $('#log_inner').scrollTop($('#log_inner').height())
    });

    function UpdateCardsLinks() {
        $('.card > img').unbind('click').click(function(evt) {
            //if (stage == 'common_turn' && is_round_master) return false;
            var ss = evt.target.src.split('/').pop();
            $('#viewport img')[0].src = 'static/cards/' + ss;
            if ((stage == 'roundmaster_turn' && is_round_master) || 
                (stage == 'common_turn' && !is_round_master) ||
                (stage == 'vote_stage' && !is_round_master)) {
                    valid_choose = true;
                    lastcardclick = evt.target;
                }
        });
    }

    s.on('update_cards', function(data) {
        $('#cardsblock_row')[0].innerHTML = '';
        for (var i = 0; i < data.length; ++i){
            $('#cardsblock_row').append(
            '<div class="card"><img src="static/cards/thumbs/' + data[i] + '"></div>'
            )
        }
        cards = data;
        UpdateCardsLinks();
    });

    s.on('update_scoreboard', function(data) {
        $('#result_outer')[0].innerHTML = '';
        for (var i = 0; i < data.length; ++i){
            var ts;
            ts = '<div class="result';
            if (data[i][0] == nickname) ts += ' mine';
            if (data[i][0] == round_master) ts += ' roundmaster';
            if (choosers[data[i][0]]) ts += ' chooser';
            ts += '">\
                    <div class="nickname">\
                        ' + data[i][0] + '\
                    </div>\
                    <div class="score">\
                        ' + data[i][1] + '\
                    </div>\
                    <div style="clear: both"></div>\
                </div>'
            $('#result_outer').append(ts);
        }
    });

    s.on('nick', function(data) {
        nickname = data;
        $('#login_link').unbind('click');
        $('#login_link')[0].style.textDecoration = 'line-through';
        $("#log_inner").append('<div class="system">You can also \
                                <a id="master_link" href="#" class="popup-link-master">become master</a></div>');
        UpdatePopupLinks();
        $('#master_link').click(function(evt) {
            $('#master')[0].focus();
        });
    });

    s.on('master', function(data) {
        $("#log_inner").append('<div class="system">Ok you are master</div>');
        $('#master_link').unbind('click');
        $('#master_link')[0].style.textDecoration = 'line-through';
        master = true;
    })

    s.on('start_round', function(data) {
        round_master = data['round_master'];
        is_round_master = data['is_round_master'];
        s.emit('update_scoreboard');
        stage = "roundmaster_turn"
        if (is_round_master) {
            choosing = true;
            $('#viewport img')[0].src = 'static/azumanga.png';
        }
        s.emit("update_cards");
    });

    s.on('common_turn', function(data) {
        is_round_master = data['is_round_master'];
        stage = 'common_turn';
        if (is_round_master) {
            $('#cardsblock_row')[0].innerHTML = '';
            choosing = false;
            cur_choose = '';
            $('.selector')[0].style.display = 'none';
        } else {
            choosing = true;
            valid_choose = false;
            $('#viewport img')[0].src = 'static/azumanga.png';
        }
    });

    s.on('choices_status', function(data) {
        choosers = data;
        s.emit('update_scoreboard');
    });

    s.on('choice', function(data) {
        $('#cardsblock_row')[0].innerHTML = '';
        choosing = false;
        cur_choose = '';
        $('.selector')[0].style.display = 'none';
    });

    s.on('vote_stage', function(data) {
        stage = 'vote_stage';
        is_round_master = data['is_round_master'];
        vars = data['variants'];
        $('#cardsblock_row')[0].innerHTML = '';
        for (var i = 0; i < vars.length; ++i){
            $('#cardsblock_row').append(
            '<div class="card"><img src="static/cards/thumbs/' + vars[i] + '"></div>'
            )
        }
        cards = data;
        UpdateCardsLinks();
        choosing = true;
        valid_choose = false;
    });

    s.on('vote', function() {
        lastcardclick.parentNode.innerHTML += '<div class="downmark">vote</div>';
        UpdateCardsLinks();
        choosing = false;
        $('.selector')[0].style.display = 'none';
    });

    s.on('break', function(data) {
        stage = 'break';
        choosing = false;
        is_round_master = data['is_round_master'];
        vars = data['variants'];
        var mstlink = -1;
        $('#cardsblock_row')[0].innerHTML = '';
        for (var i = 0; i < vars.length; ++i){
            var ts = '<div class="card"><img src="static/cards/thumbs/' + vars[i]['card'] + '">';
            if (vars[i]['master']) {
                ts += '<div class="upmark highlight">' + vars[i]['owner'] + '</div>';
                mstlink = i;
            } else {
                ts += '<div class="upmark">' + vars[i]['owner'] + '</div>';
            }
            if (vars[i]['card'] == data['my_vote']) {
                ts += '<div class="downmark highlight">' + vars[i]['cnt'] + '</div>';
            } else {
                ts += '<div class="downmark">' + vars[i]['cnt'] + '</div>';
            }
            $('#cardsblock_row').append(ts)
        }
        UpdateCardsLinks();
        if (mstlink >= 0) $('.card > img')[mstlink].click();
        var cards = [];
        var choosing = false;
        var master = false;
        var stage = 'break';
        var round_master = '';
        var is_round_master = false;
        var valid_choose = false;
        var cur_choose = '';
        var choosers = {};
        var lastcardclick = {};
    });


    $('#select').click(function(evt) {
        cur_choose = $(".viewport_inner img")[0].src.split('/').pop();
        if (stage == 'roundmaster_turn') {

            /* Предотвращаем действия по умолчанию */
            evt.preventDefault();
            evt.stopPropagation();

            /* Получаем id (последний номер в имени класса ссылки) */
            var id = "association";
            var scrollPos = $(window).scrollTop();

            /* Корректный вывод popup окна, накрытие тенью, предотвращение скроллинга */
            $('#popup-box-'+id).show();
            $('#blackout').show();
            $('html,body').css('overflow', 'hidden');

            /* Убираем баг в Firefox */
            $('html').scrollTop(scrollPos);

            $('#association').focus();
        } else if (stage == 'common_turn') {
            if (valid_choose) s.emit('choice', cur_choose);
        } else if (stage == 'vote_stage') {
            if (valid_choose) s.emit('vote', cur_choose);
        }
    });

    $('#msg_form').submit(function (evt) {
        var line = $('#msg').val()
        $('#msg').val('')
        if (nickname != '') {
            if (line == '/round') {
                s.emit('start_round');
            } else {
                s.emit('message', line);
            }
        } else {
            $("#log_inner").append("<div class='error'>" + 'You should login first' + "</div>");
        }
        return false;
    });

    $('#nick_form').submit(function (evt) {
        var line = $('#nick').val();
        $('#nick').val('');
        if (nickname == '') {
            s.emit('nick', line);
        }
        $('.close').click();
        return false;
    });

    $('#association_form').submit(function (evt) {
        var line = $('#association').val();
        $('#association').val('');
        s.emit('roundmaster_turn', {
            'description': line,
            'card': cur_choose,
        });
        $('.close').click();
        return false;
    });


    $('#master_form').submit(function (evt) {
        var line = $('#master').val()
        $('#master').val('')
        s.emit('become_master', line);
        $('.close').click();
        return false;
    });

    $('#login_link').click();
};