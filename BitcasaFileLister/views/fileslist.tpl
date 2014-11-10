<html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Bitcasa File lister</title>
        <link rel="stylesheet" href="//netdna.bootstrapcdn.com/bootstrap/3.1.1/css/bootstrap.min.css">
        <link rel="stylesheet" href="/static/bootstrap.min.css">
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
                <li><a href="/bitcasafilelister/">Home</a></li>
                <li><a href="https://github.com/rxsegrxup/BitcasaFileLister/">GitHub</a></li>
                <li><a href="https://rose-llc.com/#donate" target="_blank">Donate</a></li>
                <li><a href="https://rose-llc.com/#about" target="_blank">About</a></li>
              </ul>
            </div><!-- /.navbar-collapse -->
          </div><!-- /.container-fluid -->
        </nav>
        <ol class="breadcrumb">       
            <li><a href="/bitcasafilelister/">Home</a></li>
        % if folder.path == "/":
            % paths = [""]
        % else:
            % paths = folder.path.split("/")
        % end
        % index = 0
        % for path in paths:
            % index += len(path)
            % if path == "":
                % path = "Root"
            % else:
                % index += 1
            % end
            % if path == paths[-1] or len(paths) == 1: 
                <li class="active" title="/bitcasafilelister/files{{folder.path[:index]}}">{{path}}</li>
            % else:
                <li><a href="/bitcasafilelister/files{{folder.path[:index]}}">{{path}}</a></li>
            % end
        % end
        </ol>
        <div style="padding:0 10px;">
            <h1>Bitcasa Files</h1>
            <table class='table'>
                <tr>
                    <th style="min-width:130px;">Name</th>
                    <th>Base64 Path</th>
                </tr>
                <tr>
                    <td><a href="/bitcasafilelister/files{{parent_path}}">Up</a></td>
                    <td>{{parent_path}}</td>
                </tr>
                % for item in folder:
                    <tr>
                        % if isinstance(item, BitcasaFile):
                            % url = download_url + item.name + "?access_token=" + access_token + "&path=" + item.path
                            <td><a href="{{url}}">{{item.name}}</a></td>
                        % else:
                            <td><a href="/bitcasafilelister/files{{item.path}}">{{item.name}}</a></td>
                        % end
                        <td>{{item.path}}</td>
                    </tr>
                % end
            </table>
        </div>
            <a id="footer" class="btn btn-primary brn-long" role="button" onclick="$('body').animate({ scrollTop: 0 }, 'slow');">Top <span class="glyphicon glyphicon-arrow-up"></span></a>
        </div>
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.0/jquery.min.js"></script>
        <script src="//netdna.bootstrapcdn.com/bootstrap/3.1.1/js/bootstrap.min.js"></script>
    </body>
</html>
