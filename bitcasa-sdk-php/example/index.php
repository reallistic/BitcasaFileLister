<? 
include_once("../BitcasaClient.php");
include_once("config.php");
?>
<html><head><title>Test Login</title></head><body>
<h1>Bitcasa PHP SDK Login</h1>
<a href="<?php echo BitcasaClient::authorize(OAUTH_CLIENTID, ($_SERVER["SERVER_PORT"] == 80 ? "http://" : "https://" ) . $_SERVER["SERVER_NAME"] . ($_SERVER["REQUEST_URI"]) . "/auth.php"); ?>" > Login</a>
</body></html>
