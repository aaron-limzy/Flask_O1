
var UTC_Timing_Fixed = -480;
var UTC_Offset_Change = 0;
setInterval(Refresh_H1, 500);        //     Refresh the time.
function Refresh_H1(){
    $('#time_header').html(return_Time_String());
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
    Date_String = day_name[day] + "<br>" + year + "-" +  mon_name[month] + "-" + date + "<br>" + hr+":"+min+":"+sec;
    return Date_String;
}

function pad(number, length) {

    var str = '' + number;
    while (str.length < length) {
        str = '0' + str;
    }

    return str;

}

setInterval(updateTemp, 10000);        //     Refresh the json.
function updateTemp() {
  $.getJSON('/is_prime_return_json', function(data){
    $('#selector').html(Draw_Vertical_Table(data,"Is Prime Acc Details", "table table-dark table-striped table-bordered"));
  })
}

function Draw_Vertical_Table(table_Data, Table_Caption, Table_Class) {
    var sString = '';

    //------------- Table Header -----------------------------
    sString += '<table style="width:80%" class="' + Table_Class + '">';
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

            sString += Draw_Vertical_Table(table_Data[x], "", "minimalist_table");
        } else {
            sString += table_Data[x];
        }

        sString += "</td>";

        sString += '</tr>';
    }
    sString += '</table>';
    return sString;
}