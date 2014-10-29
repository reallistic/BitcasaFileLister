<html lang="en">
	<head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Bitcasa File lister</title>
        <link rel="stylesheet" href="//netdna.bootstrapcdn.com/bootstrap/3.1.1/css/bootstrap.min.css">
        <link rel="stylesheet" href="css/bootstrap.min.css" media="screen">
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
		        <li class="active"><a href="/">Home</a></li>
		        <li><a href="https://github.com/rxsegrxup/BitcasaFileLister/">GitHub</a></li>
		        <li><a href="/#donate" target="_blank">Donate</a></li>
                <li><a href="/#about" target="_blank">About</a></li>
		      </ul>
		    </div><!-- /.navbar-collapse -->
		  </div><!-- /.container-fluid -->
		</nav>
		<ol class="breadcrumb">
		  <li class="active">Home</li>
		</ol>
		<?php 
		include_once("bitcasa-sdk-php/BitcasaClient.php");
		include_once("bitcasa-sdk-php/config.php");
		$at = "";
		$uri = explode('?', $_SERVER['REQUEST_URI'], 2);
		$uri = $uri[0];
		$base = basename($_SERVER['PHP_SELF']);
		if( ($pos = stripos($uri, $base)) === (strlen($uri) - strlen($base)) ){
			$uri = substr($uri, 0, $pos);
		}
		if(isset($_GET["error"])){ ?>
			<div class="panel panel-danger">
				<div class="panel-heading">
					<h3 class="panel-title">An error Occured</h3>
				</div>
				<div class="panel-body">There was an error with your authorization code. Please try again</div>
            </div>
		<?php }
		if( isset($_GET["authorization_code"]) ){
			$at = "&at=".$_GET["authorization_code"];
		?>
		<div class="jumbotron">
			<h1>BitcasaFileFetcher</h1>
			<p>Your access token for the file fetcher is below.</p>
			<div class="panel panel-default">
                <div class="panel-heading">Access Token</div>
                <div class="panel-body">
                    <p><?php echo $_GET["authorization_code"]; ?></p>
                </div>
            </div>
            <p>Use this access token to run the FileFetcher like so:</p>
            <code>python getfiles.py src dest <?php echo $_GET["authorization_code"]; ?></code>
            <p>To get Base64 file paths for <code>src</code> Login below</p>
		</div>
		<?php }
		else { ?>
			<div class="jumbotron">
			<h1>BitcasaFileFetcher</h1>
			<p>To get an access token for the FileFetcher please run the following command in your console:</p>
            <code>python getfiles.py --oauth</code><br>
            <p>This will give you a link to authenticate with Bitcasa and return you here with your access token for use with the FileFetcher</p>
            <p>To get Base64 file paths Login below</p>
		</div>
		<?php } ?>
		<div class="jumbotron">
			<h1>BitcasaFileLister</h1>
			<p>Click the button below to Login to Bitcasa and retrieve your file paths.</p>
			<p><a class="btn btn-primary btn-lg" role="button" href="<?php echo BitcasaClient::authorize(OAUTH_CLIENTID, urlencode( ($_SERVER["SERVER_PORT"] == 80 ? "http://" : "https://" ) . $_SERVER["SERVER_NAME"] . $uri . "bitcasa-sdk-php/auth.php?depth=1$at")); ?>" > Login</a></p>
		</div>
		<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.0/jquery.min.js"></script>
		<script src="//netdna.bootstrapcdn.com/bootstrap/3.1.1/js/bootstrap.min.js"></script>
	</body>
</html>