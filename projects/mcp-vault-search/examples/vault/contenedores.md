# Entornos reproducibles con contenedores

Un contenedor Docker empaques el servidor con sus dependencias, permitiendo ejecutarla en máquinas distintas sin instalar Python ni gestionar ambientes virtuales. El cliente simplemente inicia un contenedor configurado con la ruta del vault.

El montaje de volúmenes permite que el contenedor lea archivos del host sin copiarlos dentro de la imagen. Montar el vault como un volumen de solo lectura impide que el servidor modifique notas.

Los contenedores facilitan la distribución del servidor a usuarios que no desean instalar código manualmente. La parte 3 de este tutorial explora configuraciones Dockerfile y Docker Compose para diferentes escenarios.
