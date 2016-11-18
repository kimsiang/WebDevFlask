function createFields() {
    $('.field').remove();
    var container = $('#container');
    for(var i = 0; i < +$('input:text').val(); i++) {
        $('<a/>', {
            'class': 'field btn btn-primary',
            'text': i + 1,
            'href': '/calo_vis/' + (i+1).toString()
        }).appendTo(container);
    }
}

function distributeFields() {
    var radius = 270;
    var fields = $('.field'), container = $('#container'),
    width = container.width(), height = container.height(),
    angle = -Math.PI/2, step = (2*Math.PI) / fields.length;
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
});

createFields();
distributeFields();
