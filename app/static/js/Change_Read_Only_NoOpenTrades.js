
$(document).ready(function(){
    var UTC_Timing_Fixed = -480;
    var UTC_Offset_Change = 0;

    var Page_Run_Count=0;           // A running counter.

    var UTC_Timing_Fixed = -480;        // Used for UTC Time offset to SGT
    var UTC_Offset_Change = 0;

    var Refresh_Page_seconds = 7;  // When to refresh the page.
    var Refresh_Page_Counter = Refresh_Page_seconds*2;  // When to refresh the page.

    var all_Changed = [];

    setInterval(Refresh_Page_seconds_call, 1000);    // To Clock in every second.

    setInterval(refresh_page_time, 200);    // To constantly refresh clock on page
    function refresh_page_time(){           // To constantly refresh clock on page.
        $('#page_time').html(return_Time_String());
    }


    function return_Time_String(){

        var e = new Date();
        var timeSone_OffSet = e.getTimezoneOffset();
        UTC_Offset_Change = (-1 * UTC_Timing_Fixed) + timeSone_OffSet;
        var d = new Date(e.getTime() + UTC_Offset_Change*60*1000);        // Get SGT


        var day = d.getDay();            // 0 - 6

        var month = d.getMonth();        // 0-11
        var year = d.getFullYear();     // yyyy


        var hr = pad(d.getHours(),2);            // 0-23
        var min = pad(d.getMinutes(),2);        // 0-59
        var sec = pad(d.getSeconds(),2);         // 0-59
        var date = pad(d.getDate(),2);

        var day_name = ["Sun" ,"Mon", "Tue", "Wed", "Thu", "Fri", "Sat" ];
        var mon_name = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "July", "Aug", "Sep", "Oct", "Nov","Dec"];



        var Date_String = "";
        Date_String = day_name[day] + " " + year + "-" +  mon_name[month] + "-" + date + " " + hr+":"+min+":"+sec;
        return Date_String;
    }

    function pad(number, length) {

        var str = '' + number;
        while (str.length < length) {
            str = '0' + str;
        }
        return str;
    }


    function Custom_Ajax_Error(xhr,status,error,error_card_id){

        var current_html = $('#' + error_card_id).html();   // To display the error. First, we need to store the HTML as we want to append.
        current_html += "------------------------- ↓" + return_Time_String() + " ↓------------------------<br>";
        current_html += "Ajax Response: " + JSON.stringify(xhr) + "<br>";
        current_html += "status: " + status + "<br>";
        current_html += "Error: " + error['message'] + "<br>" + error['stack'] + "<br><br>";
        $('#' + error_card_id ).html(current_html);  // Put it back into the Card.

        // Want to Log the time as well here.
        console.log(return_Time_String());
        console.log(xhr);
        console.log(xhr["responseText"]);
        console.log(status);
        console.log(error);
    }


    // Custom the AJAX Call. To store it into the correct table.
    // Post_Data - The data that needs to be posted
    // ajax_url - The Ajax URL to be posted to
    // table_id - Table ID that data needs to be placed
    // raw_return_id - Raw Return ID to be placed in the card
    // error_card_id - Error ID to be placed in the card
    // table_caption - Table caption to be shown
    // zero_out - Need to Zero out the table (To make it a shorter table)

    function Custom_Ajax_Call(Post_Data, ajax_url, table_id, raw_return_id, error_card_id, table_caption ) {
        $.ajax({
            url:ajax_url,
            data    : Post_Data,
            type: 'POST',
            dataType: "JSON",
            timeout: 45*1000
            ,success: function(data){


            $('#' + table_id ).html(Draw_Table(data,table_caption, "table table-hover table-sm table-responsive-sm basic_table",[]) + '<span class="right-text small-text">' + return_Time_String() + "</span>");
            $('#' + raw_return_id).html(JSON.stringify(data));
          }, error: function(xhr,status,error){
                Custom_Ajax_Error(xhr,status,error,error_card_id);
          }, complete: function(xhr,status){
                //console.log( "Into the complete Function. " );
                //console.log(xhr);
                //console.log(status);
          }
      });
    }


    // Ajax call to Change Group.
    function NoTrade_Change_Group() {

        ajax_url =   "/NoOpenTrades_ChangeGroup_ajax";
        table_id = "Change_Group_Table";
        consolidated_table_id = "Change_Group_Consolidate";
        raw_return_id = "Change_Group_Raw";
        error_card_id = "Change_Group_Error";
        table_caption = "Group Change";
        table_Sucess_Caption = "Successful Change"


        $.ajax({
            url:ajax_url,
            type: 'POST',
            dataType: "JSON",
            timeout: 45*1000
            ,success: function(data){
                if("All" in data){      // To show all the results.
                    $('#' + table_id ).html(Draw_Table(data["All"],table_caption, "table table-hover table-sm table-responsive-sm basic_table",["ERROR", "No"]) + '<span class="right-text small-text">' + return_Time_String() + "</span>");
                }
                if("Changed" in data){  // To show the successful changed.
                    all_Changed = all_Changed.concat(data["Changed"])
                    if (all_Changed.length > 0)  {    // Will only show if there are things to show.
                        $('#' + consolidated_table_id ).html(Draw_Table(all_Changed,table_Sucess_Caption, "table table-hover table-sm table-responsive-sm basic_table",["ERROR","No"]) + '<span class="right-text small-text">' + return_Time_String() + "</span>");
                    }
               }


                $('#' + raw_return_id).html(JSON.stringify(data));
          }, error: function(xhr,status,error){
                //Custom_Ajax_Error(xhr,status,error,error_card_id);
          }, complete: function(xhr,status){
                //console.log( "Into the complete Function. " );
                //console.log(xhr);
                //console.log(status);
          }
      });
    }




    function Draw_Vertical_Table(table_Data, Table_Caption, Table_Class) {
        var sString = '';

        //------------- Table Header -----------------------------
        sString += '<table class="' + Table_Class + '">';
        sString += '<caption>' + Table_Caption + '</caption>';
        sString += '<tr>';
        //------------- Table Data -----------------------------

        for (var x in table_Data) {
            //For each row, For each data

            sString += '<tr>';

            //for(var xx in table_Data[x]){	//

            var string_buffer = "";
            string_buffer += table_Data[x];

            sString += '<td><b>' + x + '</b></td>';

            if (string_buffer.search("ERROR") >= 0) {
                // If there is an error, change the color of the cell
                sString += '<td bgColor="#ff8080">';
                //sString+= '<td>';
            } else {
                sString += '<td>';
            }

            if (table_Data[x]instanceof Array == true || table_Data[x]instanceof Object == true) {
                //sString += "Is Array..." ;

                sString += Draw_Vertical_Table(table_Data[x], "", "table_orange");
            } else {
                sString += table_Data[x];
            }

            sString += "</td>";

            sString += '</tr>';
        }
        sString += '</table>';
        return sString;
    }



    // Draws a horizontal table.
    function Draw_Table(table_Data, Table_Caption, Table_Class, Alert_Words) {
        var sString = '';
        //------------- Table Header -----------------------------
        sString += '<table class="' + Table_Class + '">';
        sString += '<caption>' + Table_Caption + '</caption>';
        sString += '<tr>';

        for (var x in table_Data) {
            //For table header.
            for (var xx in table_Data[x]) {
                sString += '<th>';
                sString += xx;
                sString += '</th>';
            }
            break;
        }

        //variable instanceof Array
        sString += '</tr>';

        //------------- Table Data -----------------------------

        for (var x in table_Data) {
            //For each row

            sString += '<tr>';

            for (var xx in table_Data[x]) {
                //For each data
                var string_buffer = "";
                string_buffer += table_Data[x][xx];

                var Alert_Word_found = 0;
                for (var aw in Alert_Words) {	// Loop thru the list of alert words
                    // Loop thru the array
                    if (string_buffer.search(Alert_Words[aw]) >= 0) {
                        Alert_Word_found = 1;
                        break;
                    }
                }

                Table_Column = xx;	// Get the Column Name
                if ((xx.search("Discrepancy") >= 0) && (table_Data[x][xx] != 0)){	// If its the discrepancy Column/Row, we want to Flag out any that isn't 0.
                    Alert_Word_found = 1;
                }

                 if ((xx.search("Mismatch_count") >= 0) && (table_Data[x][xx] >= 10)){	// If its the Mismatch_count Column/Row, we want to Flag out any larger then 10
                    Alert_Word_found = 1;
                }


                if (Alert_Word_found == 1) {
                    // If there is an error, change the color of the cell
                    sString += '<td class="alert_cell">';
                    //sString+= '<td>';
                } else {
                    sString += '<td>';
                }

                if (table_Data[x][xx]instanceof Array == true || table_Data[x][xx]instanceof Object == true) {
                    //sString += "Is Array..." ;

                    sString += Draw_Vertical_Table(table_Data[x][xx], "", "table_orange ");
                } else {

                    sString += table_Data[x][xx];
                }
                sString += "</td>";

            }
            sString += '</tr>';
        }
        sString += '</table>';
        return sString;
    }



	// Get the Varible from URL if there is..
	function getQueryVariable(variable) {
       var query = window.location.search.substring(1);
       var vars = query.split("&");
       for (var i=0;i<vars.length;i++) {
               var pair = vars[i].split("=");
               if(pair[0] == variable){return pair[1];}
       }
       return(false);
	}


//    // Button Function
//    // Want to be able to toggle off and on.
//    function Toggle_Show_Zero_Position(){
//        Show_Mt4_Zero = (Show_Mt4_Zero + 1) % 2;
//        MT4_LP_Position();      // Run Ajax again. Don't really need to if we save..
//        if(Show_Mt4_Zero == 1){	// If we need to show, we need to run again.
//            $( "#btn_toggle_zero_position" ).html( "Hide Zero<br>Position" );
//            $( "#btn_toggle_zero_position" ).removeClass( "btn-warning" );
//            $( "#btn_toggle_zero_position" ).addClass( "btn-success" );
//        }else{  // Hide MT4 Zero position
//            $( "#btn_toggle_zero_position" ).html( "Show Zero<br>Position" );
//            $( "#btn_toggle_zero_position" ).removeClass( "btn-success" );
//            $( "#btn_toggle_zero_position" ).addClass( "btn-warning" );
//        }
//    }


//    // Just to play the sound.
//    function play_sound_function() {
//        if (play_Sound == 1) {
//            var audioElement = document.createElement('audio');
//            audioElement.setAttribute('src', 'static/Alert_Sounds/Music.mp3');
//            audioElement.setAttribute('autoplay', 'autoplay');
//            audioElement.load();
//            audioElement.play();
//        }
//    }

//    // Button Function
//    // Toggle play sound or not.
//    function Play_sound_Toggle() {
//        play_Sound = (play_Sound + 1) % 2;
//		if(play_Sound == 1){    // Want the sound to play
//			$( "#btn_Sound_on" ).removeClass( "btn-warning" );
//			$( "#btn_Sound_on" ).addClass( "btn-success" );
//			$("#btn_Sound_on").html( "Sound<br>On" );
//			play_sound_function();
//		}else{  // Don't want to play the sound anymore.
//		    $( "#btn_Sound_on" ).removeClass( "btn-success" );
//			$( "#btn_Sound_on" ).addClass( "btn-warning" );
//		}
//    }


//    // Button Function
//    // Toggle Send Email or not.
//    function Send_Email_Toggle() {
//        send_email_flag = (send_email_flag + 1) % 2;
//		if(send_email_flag == 1){    // Want To send the email
//
//			$( "#btn_toggle_send_email" ).removeClass( "btn-warning" );
//			$( "#btn_toggle_send_email" ).addClass( "btn-success" );
//			$("#btn_toggle_send_email").html( "Email<br>Alert: On" );
//		}else{  // Don't want to play the sound anymore.
//		    $( "#btn_toggle_send_email" ).removeClass( "btn-success" );
//			$( "#btn_toggle_send_email" ).addClass( "btn-warning" );
//			$("#btn_toggle_send_email").html( "Email<br>Alert: Off" );
//		}
//    }
//
//    // Start Function, for use to interract with DOM
//    function Message_Box(Table_Data) {
//        //var txt = "<div style=text-align: center;'>" + Draw_Table(Table_Data, "", "", "") + "</div>";
//        var txt = "<div style=text-align: center;'>" + Table_Data + "</div>";
//        swal({
//            title: '<b><u>Sound notifications.</u></b>',
//            html: txt,
//            showCancelButton: true,
//            cancelButtonText: 'No! Don\'t play sound',
//            confirmButtonColor: '#3085d6',
//            cancelButtonColor: '#d33',
//            confirmButtonText: 'Yes, Play Sound'
//        }).then((result)=>{
//            if (result.value) {
//				Play_sound_Toggle();
//				// Could play sound here too, if needed
//            } else if (// Read more about handling dismissals
//            result.dismiss === swal.DismissReason.cancel) {
//                play_Sound = 0;
//            }
//        }
//        )
//    }


    // Try Catch Block to catch if string can be parsed as json.
	function check_json(str){
        try {
          JSON.parse(str);
        } catch (e) {
          return false;
        }
        return true;
    }


    function Check_Time_Offset(){

        var d = new Date();
        var n = d.getTimezoneOffset();
        UTC_Offset_Change = (-1 * UTC_Timing_Fixed) + n;

        var e = new Date(d.getTime() + UTC_Offset_Change*60*1000);
        var d_day = d.getDay();            // 0 - 6
        var e_day = e.getDay();            // 0 - 6
        //alert("d_day = " + d_day + "  e_day = " + e_day);
    }


    function Refresh_Page(){

        Refresh_Page_Counter = 0;
        Page_Run_Count += 1;
        //Refresh_Page_Seconds
        NoTrade_Change_Group({}, "/NoOpenTrades_ChangeGroup_ajax", "Change_Group_Table", "Change_Group_Consolidate","Change_Group_Raw", "Change_Group_Error", "MT4 Change Group");
    }


    // Call in every second, will check and update button.
    function Refresh_Page_seconds_call(){
        // If the call is to be made.
        Refresh_Page_Counter++;
        if (Refresh_Page_Counter >= Refresh_Page_seconds){
            Refresh_Page();
        }
        // For the count down on the button.
        $('#Refresh_count_down').html(Refresh_Page_seconds - Refresh_Page_Counter);
    }


//    $('#btn_toggle_zero_position').click(Toggle_Show_Zero_Position);
//    $('#btn_Sound_on').click(Play_sound_Toggle);
//    $('#btn_toggle_send_email').click(Send_Email_Toggle);
    $('#btn_refresh_page').click(Refresh_Page);

});
