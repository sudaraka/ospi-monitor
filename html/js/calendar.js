var schedule_info = {};
var fetching_schedule = false;

$(function(){

	rotate_refresh(0, $('#div_loading .icon-refresh'));

	$('#btn_save_calendar_id').click(save_calendar_id);

	fetch_schedule_data();

    rotate_cog(0);

});

fetch_schedule_data = function() {
  if(fetching_schedule) return;

  fetching_schedule = true;

	$.post('/get-schedule', {
    'hash': schedule_info._data_hash
  })
		.done(function(data) {
      if(data.events || !schedule_info._data_hash) {
        schedule_info = data;
        populate_schedule_data();
      }
		})
		.fail(function(data){
			if(403 == data.status)
				$('#div_loading_failed .message').text(GET_ZONE_403);
			else if(404 == data.status)
				$('#div_loading_failed .message').text(GET_ZONE_404);

			$('#div_loading_failed').show('fast');

		})
		.always(function(){
			$('#div_loading').hide();
			keep_rotating = false;
			fetching_schedule = false;

            window.setTimeout('fetch_schedule_data();', 1000 * 10);
		});
}


// Implements the handler function called by fetch_calendar_data()
populate_schedule_data = function() {
    $('#tbl_schedule tbody *').remove();
    $('#tbl_schedule thead').show();

    $('#txt_cal_id').val(schedule_info.calendar_id);

    var rows = 0;
    for(var event_id in schedule_info.events) {
        var e = schedule_info.events[event_id];
        var on = new Date(e.turn_on.replace(/\s/, 'T'));
        var off = new Date(e.turn_off.replace(/\s/, 'T'));

        var name_td = $('<td>');
        name_td.text(e.zone_name);
        if(1 == e.running) {
            name_td
                .attr('title', 'Sprinkler running on ' + e.zone_name)
                .append(
                $('<span>')
                    .addClass('icon icon-cog')
                    .css('margin-left', '.25em')
            );
        }

        $('<tr>')
            .addClass((1 == e.running)?'success':'')
            .append(name_td)
            .append(
                $('<td>')
                .html('<strong>' + format_time(on) + '</strong><br /><small>' + on.toDateString() + '</small>')
            )
            .append(
                $('<td>')
                .html('<strong>' + format_time(off) + '</strong><br /><small>' + off.toDateString() + '</small>')
            )
        .appendTo($('#tbl_schedule tbody'))

        rows++;
    }

    if(1 > rows) {
        $('#tbl_schedule thead').hide();

        $('<tr>')
            .addClass('error')
            .append(
                $('<td>')
                    .text('No events scheduled')
            )
            .appendTo($('#tbl_schedule tbody'))
    }

    $('#div_schedule_content').show();
}

format_time = function(date) {
  var time = '';
  var h = date.getHours() % 12;

  if(0 == h) h =12;
  time += h +':';

  if(10 > date.getMinutes()) time += '0';
  time += date.getMinutes();

  time += ' ' + ((11 > date.getHours())?'AM':'PM');

  return time;
}

rotate_cog = function(angle) {
    var element = $('#tbl_schedule tbody .icon-cog');

	element.css('-webkit-transform', 'rotate(' + angle + 'deg)');
	element.css('-moz-transform', 'rotate(' + angle + 'deg)');
	element.css('-o-transform', 'rotate(' + angle + 'deg)');
	element.css('-ms-transform', 'rotate(' + angle + 'deg)');

    setTimeout(function(){
        rotate_cog(angle + 10);
    }, 100);
}

save_calendar_id = function() {
	$('#frm_calendar_id input').attr('disabled', true);

	$.post('/save-calendar-id', 'id=' + escape($('#txt_cal_id').val()))
		.done(function(result) {
			if(0 == result.error) {
				$('#div_save_success').show();
			}
			else {
				$('#div_save_failed')
					.find('.message')
						.text(result.desc)
						.end()
					.show();
			}
		})
		.always(function(){
			$('#frm_calendar_id input').attr('disabled', false);
		});

}

