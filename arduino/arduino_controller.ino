const byte ENC_A1 = 2;
const byte ENC_B1 = 3;
const byte ENC_Z1 = 20;
const byte ENC_A2 = 18;
const byte ENC_B2 = 19;
const byte ENC_Z2 = 21;
const byte LED_SWING = 22;
const byte LED_LQR   = 23;

const long PPR = 500;
const long COUNTS_PER_REV = PPR * 4;   // full quadrature = 2000 counts/rev

// for calculation of position x
const float r = 0.006365; // pulley radius in m

// storage of prev values for calculating derivative states xdot and thetadot
unsigned long prevTime = 0;
long prevCount1 = 0;
long prevCount2 = 0;

// my 4 states
float theta1 = 0.0;      // pendulum angle in rad
float thetaDot1 = 0.0;   // pendulum angular speed in rad/s
float x2 = 0.0;          // cart position in m
float xDot2 = 0.0;       // cart linear speed in m/s


// desired states
const float x_d = 0.0f;
const float theta_d = PI;
const float xDot_d = 0.0f;
const float thetaDot_d = 0.0f;

// LQR gains
const float K1 = -0.1852f;
const float K2 =  1.9435f;
const float K3 = -0.6054f;
const float K4 =  0.3230f;

// -------- switch threshold --------
const float BALANCE_BAND = 25.0f * PI / 180.0f;   // 25 degrees
bool inSwingUp = true;

//plant parameters
const float M_PEND = 0.1f;        // pendulum mass
const float M_CART = 0.136f;      // effective cart mass
const float L_CG = 0.2f;          // pendulum COM length
const float I_PEND = 0.00072f;    // pendulum inertia
const float B_PIVOT = 0.000078f;  // pendulum damping
const float C_CART = 0.63f;       // cart viscous friction
const float G_ACC = 9.81f;        // gravity
const float RM = 12.5f;           // motor armature resistance
const float KB = 0.031f;          // back-emf constant
const float KT = 0.031f;          // torque constant
const float R_MOTOR = 0.006f;     // motor pinion radius

// -------- swing-up tuning --------
const float K_SWING = 25.0f;      // tune experimentally
const float UACC_MAX = 5.0f;      // actuator/saturation limit, chosen from motor capability

//motor
float u = 0.0f;
float uApplied = 0.0f;
const byte MOTOR_IN1 = 7;
const byte MOTOR_IN2 = 8;
const byte MOTOR_ENA = 6;   // PWM pin

const float MOTOR_SUPPLY_VOLTAGE = 6.0f;

volatile long encoderCount1 = 0;       // continuous count for derivative
volatile long displayCount1 = 0;       // Z-reset count for display angle only
volatile int direction1 = 0;           // +1 = CW, -1 = CCW
volatile byte lastAB1 = 0;
volatile bool zSeen1 = false;

volatile long encoderCount2 = 0;
volatile int direction2 = 0;           // +1 = CW, -1 = CCW
volatile byte lastAB2 = 0;
volatile bool zSeen2 = false;

void updateEncoder(byte ENC_A, byte ENC_B,volatile byte &lastAB,volatile long &encoderCount,volatile int &direction,volatile long *displayCount = nullptr) {
  byte a = digitalRead(ENC_A);
  byte b = digitalRead(ENC_B);
  byte currentAB = (a << 1) | b;

  byte transition = (lastAB << 2) | currentAB;

  switch (transition) {
    // forward
    case 0b0001:
    case 0b0111:
    case 0b1110:
    case 0b1000:
      encoderCount--;
      if (displayCount != nullptr) (*displayCount)--;
      direction = -1;
      break;

    // reverse
    case 0b0010:
    case 0b0100:
    case 0b1101:
    case 0b1011:
      encoderCount++;
      if (displayCount != nullptr) (*displayCount)++;
      direction = +1;
      break;

    // invalid transition or no movement
    default:
      break;
  }

  lastAB = currentAB;
}

void isrA1() {
  updateEncoder(ENC_A1, ENC_B1, lastAB1, encoderCount1, direction1, &displayCount1);
}

void isrB1() {
  updateEncoder(ENC_A1, ENC_B1, lastAB1, encoderCount1, direction1, &displayCount1);
}

void isrZ1() {
  displayCount1 = 0;   // reset ONLY display count on Z
  zSeen1 = true;
}

void isrA2() {
  updateEncoder(ENC_A2, ENC_B2, lastAB2, encoderCount2, direction2);
}

void isrB2() {
  updateEncoder(ENC_A2, ENC_B2, lastAB2, encoderCount2, direction2);
}

/*void isrZ2() {
  encoderCount2 = 0;
  zSeen2 = true;
}*/
void applyMotorVoltage(float u) {
  // Saturate command to available supply
  if (u > MOTOR_SUPPLY_VOLTAGE) u = MOTOR_SUPPLY_VOLTAGE;
  if (u < -MOTOR_SUPPLY_VOLTAGE) u = -MOTOR_SUPPLY_VOLTAGE;

  // Convert |u| to PWM 0..255
  int pwm = (int)(255.0f * fabs(u) / MOTOR_SUPPLY_VOLTAGE);
  if (pwm > 255) pwm = 255;
  if (pwm < 0) pwm = 0;

  if (u > 0.0f) {
    digitalWrite(MOTOR_IN1, HIGH);
    digitalWrite(MOTOR_IN2, LOW);
    analogWrite(MOTOR_ENA, pwm);
  }
  else if (u < 0.0f) {
    digitalWrite(MOTOR_IN1, LOW);
    digitalWrite(MOTOR_IN2, HIGH);
    analogWrite(MOTOR_ENA, pwm);
  }
  else {
    digitalWrite(MOTOR_IN1, LOW);
    digitalWrite(MOTOR_IN2, LOW);
    analogWrite(MOTOR_ENA, 0);
  }
}

float wrapToPi(float a) {
  while (a > PI)  a -= 2.0f * PI;
  while (a < -PI) a += 2.0f * PI;
  return a;
}

float signf(float v) {
  if (v > 0.0f) return 1.0f;
  if (v < 0.0f) return -1.0f;
  return 0.0f;
}

float satSym(float v, float limit) {
  if (v > limit) return limit;
  if (v < -limit) return -limit;
  return v;
}
void printDashboard() {
  float thetaDeg = theta1 * 180.0f / PI;

  Serial.println("========================================");
  Serial.print("MODE      : ");
  Serial.println(inSwingUp ? "SWING-UP" : "LQR");

  Serial.print("x         : ");
  Serial.print(x2, 4);
  Serial.println(" m");

  Serial.print("theta     : ");
  Serial.print(theta1, 4);
  Serial.print(" rad   (");
  Serial.print(thetaDeg, 2);
  Serial.println(" deg)");

  Serial.print("xDot      : ");
  Serial.print(xDot2, 4);
  Serial.println(" m/s");

  Serial.print("thetaDot  : ");
  Serial.print(thetaDot1, 4);
  Serial.println(" rad/s");

  Serial.print("u_raw     : ");
  Serial.print(u, 2);
  Serial.println(" V");

  Serial.print("u_applied : ");
  Serial.print(uApplied, 2);
  Serial.println(" V");

  Serial.println("========================================");
  Serial.println();
}

void setup() {
  pinMode(ENC_A1, INPUT);
  pinMode(ENC_B1, INPUT);
  pinMode(ENC_Z1, INPUT);

  pinMode(ENC_A2, INPUT);
  pinMode(ENC_B2, INPUT);
  pinMode(ENC_Z2, INPUT);

  Serial.begin(115200);

  lastAB1 = (digitalRead(ENC_A1) << 1) | digitalRead(ENC_B1);
  lastAB2 = (digitalRead(ENC_A2) << 1) | digitalRead(ENC_B2);

  attachInterrupt(digitalPinToInterrupt(ENC_A1), isrA1, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC_B1), isrB1, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC_Z1), isrZ1, RISING);

  attachInterrupt(digitalPinToInterrupt(ENC_A2), isrA2, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC_B2), isrB2, CHANGE);
  // attachInterrupt(digitalPinToInterrupt(ENC_Z2), isrZ2, RISING);
  pinMode(LED_SWING, OUTPUT);
  pinMode(LED_LQR, OUTPUT);

  digitalWrite(LED_SWING, LOW);
  digitalWrite(LED_LQR, LOW);

  prevTime = micros();
  prevCount1 = encoderCount1;
  prevCount2 = encoderCount2;

  //motor
  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  pinMode(MOTOR_ENA, OUTPUT);

  applyMotorVoltage(0.0f);  

  Serial.println("Full quadrature with Z reset started");
}

void loop() {
  static unsigned long lastPrint = 0;
  unsigned long now = micros();
  // ----- state and derivative update every 5 ms -----
  if (now - prevTime >= 5000UL) {   // 5000 us = 5 ms
    noInterrupts();
    long rawCount1 = encoderCount1;     // continuous count
    long dispCount1 = displayCount1;    // Z-reset count for display
    long rawCount2 = encoderCount2;
    interrupts();

    float dt = (now - prevTime) / 1000000.0f;   // seconds

    // pendulum angle from display count (resets on Z)
    long wrappedCount1 = dispCount1 % COUNTS_PER_REV;
    if (wrappedCount1 < 0) wrappedCount1 += COUNTS_PER_REV;
    theta1 = (wrappedCount1 * 2.0f * PI) / COUNTS_PER_REV;   // rad

    // cart position from continuous cart count
    x2 = r * (rawCount2 * 2.0f * PI) / COUNTS_PER_REV;       // m

    // derivatives from continuous counts only
    thetaDot1 = ((rawCount1 - prevCount1) * 2.0f * PI) / (COUNTS_PER_REV * dt);      // rad/s
    xDot2     = ((rawCount2 - prevCount2) * 2.0f * PI * r) / (COUNTS_PER_REV * dt);  // m/s
    // SWITCHING LOGIC: Swing-up if far from upright,
  // LQR if inside ±25 deg around upright
  // --------------------------------------------------
  float thetaErr = wrapToPi(theta1 - PI);
  inSwingUp = (fabs(thetaErr) > BALANCE_BAND);

  if (inSwingUp) {
    // ---------------- SWING-UP ----------------
    digitalWrite(LED_SWING, HIGH);
    digitalWrite(LED_LQR, LOW);
    // Energy of pendulum
    float E  = 0.5f * (I_PEND + M_PEND * L_CG * L_CG) * thetaDot1 * thetaDot1
             + M_PEND * G_ACC * L_CG * (1.0f - cos(theta1));

    // Desired energy at upright
    float Er = 2.0f * M_PEND * G_ACC * L_CG;

    // Swing-up acceleration command from notes:
    // u_acc = sat( k*(E-Er)*sign(thetaDot*cos(theta)) )
    float u_acc = K_SWING * (E - Er) * signf(thetaDot1 * cos(theta1));
    u_acc = satSym(u_acc, UACC_MAX);

    // Convert acceleration command -> force using Eq. (23)
    float denom = I_PEND + M_PEND * L_CG * L_CG;

    float F = (M_CART + M_PEND) * u_acc
            + C_CART * xDot2
            - M_PEND * L_CG * thetaDot1 * thetaDot1 * sin(theta1)
            - M_PEND * L_CG *
              ((B_PIVOT * thetaDot1
               + M_PEND * L_CG * u_acc * cos(theta1)
               + M_PEND * G_ACC * L_CG * sin(theta1)) / denom) * cos(theta1);

    // Convert force -> motor voltage using Eq. (21)
    u = (F * RM * R_MOTOR * R_MOTOR + KT * KB * xDot2) / (KT * R_MOTOR);
  }
  else {
    // ---------------- LQR ----------------
    digitalWrite(LED_SWING, LOW);
    digitalWrite(LED_LQR, HIGH);
    // u = -K*(X - Xd), with
    // X  = [x, theta, xdot, thetadot]
    // Xd = [0, pi, 0, 0]
        // LQR state errors
    float ex = x2 - x_d;
    float eTheta = theta1 - theta_d;
    float exDot = xDot2 - xDot_d;
    float eThetaDot = thetaDot1 - thetaDot_d;

    // Wrap angle error to [-pi, pi]
    while (eTheta > PI)  eTheta -= 2.0f * PI;
    while (eTheta < -PI) eTheta += 2.0f * PI;

    // u = -K*(X - Xd)
    u = -(
          K1 * ex
        + K2 * eTheta
        + K3 * exDot
        + K4 * eThetaDot
        );

    // Apply voltage command to motor driver
  }
    applyMotorVoltage(u);
    uApplied = u;
    if (uApplied > MOTOR_SUPPLY_VOLTAGE) uApplied = MOTOR_SUPPLY_VOLTAGE;
    if (uApplied < -MOTOR_SUPPLY_VOLTAGE) uApplied = -MOTOR_SUPPLY_VOLTAGE;
    prevCount1 = rawCount1;
    prevCount2 = rawCount2;
    prevTime = now;
  }

 if (now - lastPrint >= 200000UL) {   // 200 ms
  lastPrint = now;
  printDashboard();
}
}