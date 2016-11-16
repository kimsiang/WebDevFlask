/*
using:
    circular positioning code:
        http://stackoverflow.com/a/10152437/1644202
    point at:
        http://pointat.idenations.com/api

depends on:
    jquery
    https://github.com/thomas-dotworx/jqrotate (pointat)
*/


function createFields() {
    $('.field').remove();
    var container = $('#container');
    for(var i = 0; i < +$('input:text').val(); i++) {
        $('<div/>', {
            'class': 'field',
            'text': i + 1,
        }).appendTo(container);
    }
}

function distributeFields(deg) {
    deg = deg || 0;
    var radius = 200;
    var fields = $('.field:not([deleting])'), container = $('#container'),
        width = container.width(), height = container.height(),
        angle = deg || Math.PI*3.5, step = (2*Math.PI) / fields.length;
    fields.each(function() {
        var x = Math.round(width/2 + radius * Math.cos(angle) - $(this).width()/2);
        var y = Math.round(height/2 + radius * Math.sin(angle) - $(this).height()/2);
        if(window.console) {
            console.log($(this).text(), x, y);
        }
        $(this).css({
            left: x + 'px',
            top: y + 'px'
        });
        angle += step;
    });
}

$('input').change(function() {
    createFields();
    distributeFields();
    initPointAt();
});

var timer = null,
    timer2 = null;
$('#addone').click(function() {
    // do not append to current, otherwise you see it moving through the container
    $('.field').addClass('moveAni');
    
    $('<div/>', {
            'class': 'field',
            'text': $('.field').length +1
    })
    
    .css({
        left: $('#container').width()/2-25 + 'px',
        top: $('#container').height()/2-25 + 'px'})
    .addClass('moveAni')
    
    .appendTo('#container')
    .pointat({
        target: "#center",
        defaultDirection: "down"
    });
    
    distributeFields();

    // without css:
    //$('.field').pointat("updateRotation");
    
    // with css: for css move animation
    clearInterval(timer); clearTimeout(timer2);
    timer = setInterval(function() {
      	$('.field').pointat({
            target: "#center",
            defaultDirection: "down"
    		}); // does not seem to update correctly: .pointat("updateRotation")
    }, 20);
    timer2 = setTimeout(function() {
      	clearInterval(timer);
    }, 420); // css animation timeout, interval +1 extra to update after the ani
    
    // update input field
    $('input:text').val($('.field').length);
});

$('#delone').click(function() {
    $('#container .field:not([deleting]):last')
    .attr('deleting', 'true')
    .css({
        left: $('#container').width()/2-25 + 'px',
        top: $('#container').height()/2-25 + 'px'
    })
    .fadeOut(400, function() {
        $(this).remove();
    });

		// do distribiution as if the currently out-animating fields are gone allready
    distributeFields();

    clearInterval(timer); clearTimeout(timer2);
    timer = setInterval(function() {
        $('.field').pointat({
            target: "#center",
            defaultDirection: "down"
        }); // does not seem to update correctly: .pointat("updateRotation")
    }, 20);
    timer2 = setTimeout(function() {
      	clearInterval(timer);
    }, 420); // css animation timeout, interval +1 extra to update after the ani
    
    // update input field
    $('input:text').val($('.field:not([deleting])').length); // update yet
});


createFields();
distributeFields();
initPointAt();

    


function initPointAt() {
    $('.field').pointat({
        target: "#center",
        defaultDirection: "down",
        xCorrection: -20,
        yCorrection: -20
    });
}