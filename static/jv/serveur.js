

//envoie les informations sur le serveur python
function sendData(value) { 

  $.ajax({ 
      url: '/process', 
      type: 'POST', //type de requete
      contentType: 'application/json', 
      data: JSON.stringify({ 'value': value }), 
      success: function(response) { 
          //document.getElementById('output').innerHTML = response.result; 
          //console.log(response.result);
                }, 
      error: function(error) { 
          console.log(error); 
      } 
  }); 
} 

function sendDataGET(value) {
  $.ajax({
    url : '/GET',
    type: 'GET',
    data: value,
    success: function(response) { 
      //document.getElementById('output').innerHTML = response.result; 
      console.log(response.result);
            }, 
    error: function(error) { 
        console.log(error); 
    }
  });
}

// Fonction pour afficher l'information
function afficherInformation(info) {
  //document.getElementById('info').innerText = 'Touche : ' + info;

  // Envoie l'information au serveur python
  sendData(info);
}

function afficherGet(info){
  sendDataGET(info);
}
          
// Fonction de gestion de l'événement
function gestionnaireEvenement(e) {
  // Récupérer le code de la touche
  const codeTouche = e.code;

  // Afficher l'information
  afficherInformation(codeTouche);
}



