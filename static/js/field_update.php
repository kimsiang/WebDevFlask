<?php

include_once("config.php");
mysql_connect(DB_HOST,DB_USER,DB_PASSWORD) or die(mysql_error());
mysql_select_db(DB_NAME) or die(mysql_error());
define('DB_TABLE','gluing_progress'); 

$xtal_serial_num = "";
$field = "";
$val = "";


if ( array_key_exists( 'xtal_serial_num', $_GET ) ) $xtal_serial_num = $_GET['xtal_serial_num'];
if ( array_key_exists( 'field', $_GET ) ) $field = $_GET['field'];
if ( array_key_exists( 'val', $_GET ) ) $val = $_GET['val'];

if ( $xtal_serial_num == "" || $field == "" ) die("Bad input parameters");


$isOk=TRUE;
// update database
$query="UPDATE `".DB_TABLE."` SET `".$field."`='".$val."' WHERE `xtal_serial_num`='".$xtal_serial_num."'";
$result = mysql_query($query) or die(mysql_error());
if ( $result === FALSE )
    $isOk = FALSE;

    // read back from database
if ( $isOk )
{
    $readback='';
    $query="SELECT `".$field."` FROM `".DB_TABLE."` WHERE `xtal_serial_num`='".$xtal_serial_num."'";
    $result = mysql_query($query) or die(mysql_error());
    if ( $result === FALSE )
	$isOk = FALSE;
    else
    {
	$readback=$result[0];
#	$result->CloseCursor();
	if ( $readback != $val ) $isOk=FALSE;
    }
}

header("Content-type: image/png");

if ( $isOk )
    readfile("gluing.png");
else
    readfile("gluing.png");

?>
