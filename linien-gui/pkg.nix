{ lib
, buildPythonPackage
, version
, src
, pyqtgraph
, pyqt5
, superqt
, click
, linien-client
, qt5
, makeDesktopItem
, copyDesktopItems
, graphicsmagick
, app-paths
}:

buildPythonPackage rec {
  pname = "linien-gui";
  inherit version;

  inherit src;

  buildInputs = [
    qt5.qtbase
    qt5.qtwayland
  ];

  propagatedBuildInputs = [
    app-paths
    pyqtgraph
    pyqt5
    superqt
    click
    linien-client
  ];

  nativeBuildInputs = [
    qt5.wrapQtAppsHook
    copyDesktopItems
    graphicsmagick
  ];
  preFixup = ''
    makeWrapperArgs+=("''${qtWrapperArgs[@]}")
  '';
  desktopItems = makeDesktopItem {
    name = meta.mainProgram;
    exec = meta.mainProgram;
    icon = meta.mainProgram;
    desktopName = meta.mainProgram;
    comment = meta.description;
    type = "Application";
    categories = [ "Science" ];
  };

  postInstall = ''
    mkdir -p $out/share/icons/hicolor/256x256/apps/
    gm convert linien_gui/icon.ico $out/share/icons/hicolor/256x256/apps/${meta.mainProgram}.png
  '';

  pythonImportsCheck = [
    "linien_gui"
  ];

  meta = with lib; {
    description = "Graphical user interface of the Linien spectroscopy lock application";
    homepage = "https://github.com/linien-org/linien";
    license = licenses.gpl3;
    mainProgram = "linien";
  };
}
