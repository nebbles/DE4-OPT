global n D h App mpp g M N Ttr;
tic
%Constants
n = 50;  % Number of floors
D = 4*n;  % Distance to travel
rho = 360;  % Whole lift density (incl air)
h = 2;  % Lift height
App = 0.36;  % Lift floor area per person
mpp = 75;  % Mass Per Person
g = 9.81;  % Gravity
X = 100;  % People to be moved
M = (mpp + rho*App*h)*D;  % Mass of lift dependant on C
Pph = 20;  % £ per hour employee time
PpkWh = 0.13;  % £ per kilowatt hour
Amax = 20;  % Maximum lift surface area
N = 8;  % Amount of lifts
Ttr = 0.239;  % Throughput traffic in avg. ( from Greenberg )
Cmax = Amax/App; % Maximum capcity value

% Price weightings
%variables = [[],[],[],[]];
accels = [];
caps = [];
velocs = [];
ws = [];
%W = [0,0];
for w = linspace(0,1,100)
    %W(1) = PpkWh/3.6*10^-8;  % Price of Energy per Joule
    %W(2) = Pph/60/60;  % Cost of employee time per second
    W(1) = w;
    W(2) = 1-w;

%x = [acceleration, Capacity, max_velocity]
    x0 = [0.5,1,10];
    A = [0,1,0];
    b = [55];
    Aeq = [];
    beq = [];
    lb = [0.01,1,0.01];
    ub = [1.5,X,20];

    liftOpt = @(x)W(1)*M*x(1)*x(2) + ...
             W(2)*(Ttr/N - (x(2)/(2*(x(3)/x(1) + D/x(3)))));
    x = fmincon(liftOpt,x0,A,b,Aeq,beq,lb,ub,@mycon);
    accels = [accels, x(1)];
    caps = [caps, x(2)];
    velocs = [velocs, x(3)];
    ws = [ws, w];
    %variables = append([x(1),x(2),x(3),w]);
    %variables(2) = [variables(2), x(2)];
    %variables(3) = [variables(3), x(3)];
end

%function f = liftOpt(a,C,vm)
%    global W1 M W2 D
 %   f =W1*M*a*C + W2(D*a + vm^2)/a*vm;
plot(accels,'-.r')
hold on
plot(caps, 'g--')
plot(velocs, 'b-')
hold off
%end
Ep = W(1)*(M*x(1)*x(2))
Time = x(3)/x(1) + D/x(3);
Tpp = x(2)/(2*(x(3)/x(1) + D/x(3)));
TC = W(2)*(Ttr/N - Tpp)
%liftOpt = Ep + W(2)*Tpp
toc

function [c,ceq] = mycon(x)
    global D Ttr N
    c(1) = D - (x(3)^2)/x(1);
    c(2) = (x(2)/(2*(x(3)/x(1) + D/x(3)))) - Ttr/N;
    ceq = [];
end


function TP = totalprice(X,p,T,c)
    TP = p*T*X;
    while X > 0
        X = X - c;
        TP = TP + 2*p*T*X;
    end
end