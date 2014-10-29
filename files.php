<html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Bitcasa File lister</title>
        <link rel="stylesheet" href="//netdna.bootstrapcdn.com/bootstrap/3.1.1/css/bootstrap.min.css">
        <link rel="stylesheet" href="css/bootstrap.min.css" media="screen">
        <style type="text/css">
            #footer {
              position: fixed;
              bottom: 0;
              right:0;
            }
            a:link, a:hover, a:active, a:visited, a{
                color:#2a6496;
            }
            p, .table>tbody>tr>td{
                word-break:break-all;
            }
            .hideSmallScreen{
                display: none;
            }
            @media (min-width: 768px){
                .hideSmallScreen{
                    display: inherit;
                }
                
            }
        </style>
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
                <li><a href="/#donate" target="_blank">Donate</a></li>
                <li><a href="/#about" target="_blank">About</a></li>
              </ul>
            </div><!-- /.navbar-collapse -->
          </div><!-- /.container-fluid -->
        </nav>
        <ol class="breadcrumb">       
          <li><a href="/bitcasafilelist/">Home</a></li>
          <li class="active">Access Token and Files</li>
        </ol>
        <div style="padding:0px 10px;">
            <h1>Bitcasa Access Token and Files</h1>

            <?php
            include_once("./bitcasa-sdk-php/BitcasaClient.php");
            include_once("./bitcasa-sdk-php/config.php");
            include_once("./bitcasa-sdk-php/BitcasaUtils.php");

            $at=$_GET["access_token"];
            $newat=$_GET["at"];
            $uri = explode('?', $_SERVER['REQUEST_URI'], 2);
            $uri = $uri[0];
            $base = basename($_SERVER['PHP_SELF']);
            if( ($pos = stripos($uri, $base)) === (strlen($uri) - strlen($base)) ){
                $uri = substr($uri, 0, $pos);
            }
            $urlprefix=($_SERVER["SERVER_PORT"] == 80 ? "http://" : "https://" ) . $_SERVER["SERVER_NAME"] . $uri .
                    "files.php?access_token=$at&root=";

            $urlprefix2="https://developer.api.bitcasa.com/v1/files/";
            if(isset($_GET['root'])){
                $root=$_GET["root"];
                if($root !="/" && strlen($root) > 1){
                    $parent = substr($root, 0,strpos($root, "/", 1)===false?1:strpos($root, "/", 1));
                }
                else{
                    $parent = "/";
                }
            }
            else{
                $root ="/";
                $parent ="/";
            }
            if( isset($_GET["at"]) ){
            ?>
            <div style="margin-left:30px;margin-bottom:20px;">
                <p>Your access token for the file fetcher is below.</p>
                <div class="panel panel-default">
                    <div class="panel-heading">Access Token</div>
                    <div class="panel-body">
                        <p><?php echo $newat; ?></p>
                    </div>
                </div>
                <p>Use this access token to run the FileFetcher like so:</p>
                <code>python getfiles.py src dest <?php echo $newat; ?></code>
            </div>
            <?php }
            else { ?>
                <div style="margin-left:30px;margin-bottom:20px;">
                    <p>To get an access token for the FileFetcher please run the following command in your console:</p>
                    <code>python getfiles.py --oauth</code><br>
                    <p>This will give you a link to authenticate with Bitcasa and return you here with your access token for use with the FileFetcher</p>
                </div>
                <div class="panel panel-danger">
                    <div class="panel-heading">Access Token only for those that have not upgraded to the new FileFetcher</div>
                    <div class="panel-body">
                        <p><?php echo $at; ?></p>
                    </div>
                </div>
            <?php } ?>
            <?php
            if(isset($_GET['depth'])){
                $dpth = $_GET['depth'];
            }
            else{
                $dpth = 1;
            }

            $client = new BitcasaClient();
            $client->setAccessTokenFromRequest();
            $error=false;
            try {
                $items = $client->getFolderFromPath($root);
                
                if($root == "/" || $root == NULL){
                    $oitem = BitcasaInfiniteDrive::listAll($client);
                }
                else{
                    $oitem = array();
                }
                
            }
            catch (Exception $ex) {
                echo '<div class="panel panel-danger"><div class="panel-heading"><h3 class="panel-title">An error Occured</h3></div><div class="panel-body">';
                echo "<a href='".$urlprefix."/' >Drive Root</a>";
                echo "<pre>";
                var_dump($ex);
                echo "</pre></div></div>";
                $error=true;
            }
            if(!$error){
                echo "<table class='table'>";
                ?>
                <tr><th style="min-width:130px;">Name</th><th>Base64 Path</th><th class="hideSmallScreen">Sync Type</th></tr>
                <?php
                echo "<tr><td>";
                        echo "<a href='".$urlprefix.$parent."' >Up</a>";
                        echo "</td><td class=\"hideSmallScreen\">"
                        . "</td><td>" . $parent . "</td></tr>";
                foreach ($items as $key => $item) {
                    echo "<tr><td>";
                        if($item->getType() == 1){
                            echo "<a href='".$urlprefix.$item->getPath()."' >" . $item->getName() ."</a>";
                        }
                        else{
                            echo "<a href='".$urlprefix2.$item->getName()."?access_token=$at&path=".$item->getPath()."' >" . $item->getName() ."</a>";
                        }
                        echo "</td><td>" . $item->getPath() . "</td>"
                        . "</td><td class=\"hideSmallScreen\">" . $item->getSyncType()."</tr>";
                }
                foreach ($oitem as $key => $item) {
                    echo "<tr><td>";
                        if($item->getType() == 1){
                            echo "<a href='".$urlprefix.$item->getPath()."' >" . $item->getName() ."</a>";
                        }
                        else{
                            //echo $item->getName();
                            echo "<a href='".$urlprefix2.$item->getName()."?access_token=$at&path=".$item->getPath()."' >" . $item->getName() ."</a>";
                        }
                        echo "</td><td>" . $item->getPath() . "</td>"
                        . "</td><td class=\"hideSmallScreen\">" . $item->getSyncType()."</tr>";
                }

                echo "</table>";
            }
            ?>
        </div>
            <a id="footer" class="btn btn-primary brn-long" role="button" onclick="$('body').animate({ scrollTop: 0 }, 'slow');">Top <span class="glyphicon glyphicon-arrow-up"></span></a>
        </div>
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.0/jquery.min.js"></script>
        <script src="//netdna.bootstrapcdn.com/bootstrap/3.1.1/js/bootstrap.min.js"></script>
    </body>
</html>
