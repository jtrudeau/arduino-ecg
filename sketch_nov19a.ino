void setup() {
  Serial.begin(9600);
  pinMode(2, INPUT); // sets up the LO+ input pin
  pinMode(3, INPUT); // sets up the LO- input pin
}

void loop() {
  
  if((digitalRead(3) == 1) || (digitalRead(2) == 1)){
    Serial.println(0);
  }
  else{
    // Reads A0 (output) and sends it to serial
    Serial.println(analogRead(A0));
  }
  delay(10);
}
