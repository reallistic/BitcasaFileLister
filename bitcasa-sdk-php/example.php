<html lang="en">
	<head>
		<meta charset="utf-8">
		<title>Bitcasa File lister</title>
		<link rel="stylesheet" href="../css/bootstrap.min.css" media="screen">
	</head>
	<body>
		<nav class="navbar navbar-default" role="navigation">
		  <div class="container-fluid">
		    <!-- Brand and toggle get grouped for better mobile display -->
		    <div class="navbar-header">
		      <button type="button" class="navbar-toggle" data-toggle="collapse" data-target="#bs-example-navbar-collapse-1">
		        <span class="sr-only">Toggle navigation</span>
		        <span class="icon-bar"></span>
		        <span class="icon-bar"></span>
		        <span class="icon-bar"></span>
		      </button>
		      <a class="navbar-brand" href="#">Bitcasa File Lister</a>
		    </div>

		    <!-- Collect the nav links, forms, and other content for toggling -->
		    <div class="collapse navbar-collapse" id="bs-example-navbar-collapse-1">
		      <ul class="nav navbar-nav">
		        <li><a href="/bitcasafilelist/">Home</a></li>
		        <li><a href="https://github.com/rxsegrxup/BitcasaFileLister/">GitHub</a></li>
		        <li><a href="/donate/">Donate</a></li>
		        <li><a href="/about/">About</a></li>
		      </ul>
		    </div><!-- /.navbar-collapse -->
		  </div><!-- /.container-fluid -->
		</nav>
		<ol class="breadcrumb">		  
		  <li><a href="/bitcasafilelist/">Home</a></li>
		  <li class="active">Access Token and Files</li>
		</ol>
	<h1>Bitcasa Access Token and Files</h1>
<?php
include_once("BitcasaClient.php");
include_once("config.php");
include_once("BitcasaUtils.php");

$at=$_GET["access_token"];
if(isset($_GET['depth'])){
	$dpth = $_GET['depth'];
}
else{
	$dpth = 1;
}
$files = json_decode(basicCurlGet("https://developer.api.bitcasa.com/v1/folders/?access_token=$at&depth=$dpth"));
echo "<pre>";
print_r($files);
echo "</pre>";

exit;

?>

		<input type="hidden" value="<?php echo BitcasaClient::authorize(OAUTH_CLIENTID, ($_SERVER["SERVER_PORT"] == 80 ? "http://" : "https://" ) . $_SERVER["SERVER_NAME"] . ($_SERVER["REQUEST_URI"]) . "bitcasa-sdk-php/auth.php"); ?>" id="authurl">
		<input type="number" min="1" max="5" name="maxdepth" id="maxdepth" value="1" /> Depth of file traverse
		<input type="button" value="Set" onclick="$('#bcloginlink').attr('href',$('#authurl').val()+'?depth='+$('#maxdepth').val())">
		<br />
		<a id="bcloginlink" href="<?php echo BitcasaClient::authorize(OAUTH_CLIENTID, ($_SERVER["SERVER_PORT"] == 80 ? "http://" : "https://" ) . $_SERVER["SERVER_NAME"] . ($_SERVER["REQUEST_URI"]) . "bitcasa-sdk-php/auth.php"); ?>?depth=1" > Login</a>
		<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.0/jquery.min.js"></script>
		<script src="//netdna.bootstrapcdn.com/bootstrap/3.1.1/js/bootstrap.min.js"></script>
	</body>
</html>