<?php
include_once("BitcasaClient.php");
include_once("config.php");

$client_id = OAUTH_CLIENTID;
$secret = OAUTH_SECRET;

if (!isset($_GET['authorization_code']))
{
	header("Location: ../?error=true");
	exit;
}

$client = new BitcasaClient();

try {
	if (!$client->authenticate($client_id, $secret)) {
		die("failed to authenticate");
	}
}
catch (Exception $ex) {
	header("Location: ../?error=true");
	exit;
}
$at = isset($_GET["at"]) ? "&at=" . $_GET["at"] : "";
header('Location: ../files.php?access_token=' . $client->getAccessToken() . $at ,true, 302);
exit;

?>
