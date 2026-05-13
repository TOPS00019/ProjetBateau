#include "arduino_secrets.h"


#include <string.h>
#include <AccelStepper.h>

#define MotorInterfaceType 4


AccelStepper stepper1(MotorInterfaceType, 13, 12, 14, 27);


AccelStepper stepper2(MotorInterfaceType, 26, 25, 33, 32);



String current;
String movement;
float value = 0;




const float pasParTour = 2100;
const float cmParTour = 25; 
const float pasParCm = pasParTour / cmParTour;
const float pasParDegre = 1;



void setup() {
  stepper1.setMaxSpeed(200);      
  stepper1.setAcceleration(50);   

  stepper2.setMaxSpeed(200);
  stepper2.setAcceleration(50);
  Serial.begin(115200);

  
  
}

void loop() {
  if(Serial.available() > 0){
        String commande = Serial.readStringUntil('\n');
        
        current = commande;
      if(current.length()>=6){
        movement = current.substring(0,6);
        value = current.substring(6).toFloat();
      }
        
    }
  
   
  if(movement == "avance"){
    stepper1.enableOutputs();
    stepper2.enableOutputs();
    stepper1.move(value * pasParCm);
    stepper2.move(-(value * pasParCm));
    current = "";
    movement = "";

    
  }
  if(movement == "recule"){
    stepper1.enableOutputs();
    stepper2.enableOutputs();
    stepper1.move(-value * pasParCm);
    stepper2.move((value * pasParCm));
    current = "";
    movement = "";

    
  }
  if(movement == "tourne" && value != 0 ){
    stepper1.enableOutputs();
    stepper2.enableOutputs();
    stepper1.move(pasParDegre * value);
    stepper2.move(pasParDegre * value);
    current = "";
    movement = "";

    
  }
  
  if(movement == "arrete"){
    stepper1.stop();
    stepper2.stop();
    // stepper1.move(0);
    // stepper2.move(0);
    current = "";
    movement = "";

    
  }
  if(current == "test1"){
    stepper1.enableOutputs();
    stepper1.move(2100);  
    current = "";
    movement = "";
  }
  if(current == "test2"){
    stepper2.enableOutputs();
      stepper2.move(2100);  
      current = "";
      movement = "";
  }
  if(current == "test3"){
    stepper1.enableOutputs();
      stepper1.move(-2100); 
      current = "";
      movement = "";
  }
  if(current == "test4"){
    stepper2.enableOutputs();
      stepper2.move(-2100); 
      current = "";
      movement = "";
  }

  stepper1.run();
  stepper2.run();
  
  if(stepper1.distanceToGo() == 0){
    stepper1.disableOutputs();
  }
  if(stepper2.distanceToGo() == 0){
    stepper2.disableOutputs();
  }
}