#include <iostream>
#include <vector>
#include <cmath>
#include <string>
#include <utility>
#include <queue>
#include <algorithm>

using namespace std;

const int dx[] = {1, -1, 0, 0};
const int dy[] = {0, 0, 1, -1};

class BateauInfo {
    public:
        string MMSI;
        int x;
        int y;
        float angle;

        BateauInfo(string mmsi, int x_init, int y_init, float angle_init) {
            MMSI = mmsi;
            x = x_init;
            y = y_init;
            angle = angle_init;
        }
};

// CORRECTION BUG 1 : prototype avant la classe Bateau
vector<pair<int,int> > carre_entoure(vector<BateauInfo> infosBateaux, int N);
vector<pair<int,int> > itineraire(pair<int,int> depart, pair<int,int> destination, vector<BateauInfo> infosBateaux, int N);

class Bateau {
    private:
        string MMSI;
    public:
        float vitesse;
        int x;
        int y;
        float angle;
        vector<BateauInfo> infosBateaux;
        vector<pair<int,int> > destination;
        vector<pair<int,int> > itineraire_courant;
        int N;

        // CORRECTION BUG 4 : plus d'init inline, tout dans le constructeur
        Bateau(string mmsi, int x_init, int y_init, float angle_init, float vitesse_init,
               vector<pair<int,int> > destination_init, int N_init)
            : MMSI(mmsi), x(x_init), y(y_init), angle(angle_init),
              vitesse(vitesse_init), destination(destination_init), N(N_init) {}

        void MiseaJourItineraire() {
            if (destination.empty()) {
                return;
            }

            // CAS 1 : arrivé au prochain waypoint (front) → on le retire et on continue
            if (make_pair(x, y) == destination.front()) {
                destination.erase(destination.begin());
                // Recalculer l'itinéraire vers le nouveau waypoint s'il en reste
                if (!destination.empty()) {
                    itineraire_courant = itineraire(make_pair(x, y), destination.front(), infosBateaux, N);
                } else {
                    itineraire_courant.clear();
                }
            }
            // CAS 2 : chemin bloqué (itinéraire retourne {-1,-1})
            else if (itineraire_courant.size() == 1 &&
                     itineraire_courant.back() == make_pair(-1, -1)) {

                cout << "Chemin bloque, tentative de deblocage..." << endl;

                vector<pair<int,int> > interdites = carre_entoure(infosBateaux, N);
                bool trouve = false;

                // CORRECTION BUG 2 : conditions de boucle corrigées
                for (int i = max(0, x-1); i <= min(N-1, x+1) && !trouve; i++) {
                    for (int j = max(0, y-1); j <= min(N-1, y+1) && !trouve; j++) {
                        if (find(interdites.begin(), interdites.end(), make_pair(i, j)) == interdites.end()) {
                            destination.insert(destination.begin(), make_pair(i, j));
                            itineraire_courant = itineraire(make_pair(x, y), make_pair(i, j), infosBateaux, N);
                            trouve = true;
                        }
                    }
                }
            }
        }
};

// CORRECTION BUG 5 : on évite les doublons dans la liste des cases interdites
vector<pair<int,int> > carre_entoure(vector<BateauInfo> infosBateaux, int N) {
    vector<pair<int,int> > interdites;

    for (int k = 0; k < (int)infosBateaux.size(); k++) {
        BateauInfo &b = infosBateaux[k];

        pair<int,int> bc = make_pair(b.x, b.y);
        if (find(interdites.begin(), interdites.end(), bc) == interdites.end())
            interdites.push_back(bc);

        for (int i = 0; i < 4; i++) {
            int nx = b.x + dx[i];
            int ny = b.y + dy[i];
            if (nx >= 0 && nx < N && ny >= 0 && ny < N) {
                pair<int,int> voisin = make_pair(nx, ny);
                if (find(interdites.begin(), interdites.end(), voisin) == interdites.end())
                    interdites.push_back(voisin);
            }
        }
    }
    return interdites;
}

vector<pair<int,int> > itineraire(pair<int,int> depart, pair<int,int> destination,
                                   vector<BateauInfo> infosBateaux, int N)
{
    vector<vector<bool> > visited(N, vector<bool>(N, false));

    // Bloquer bateaux + voisins
    for (int k = 0; k < (int)infosBateaux.size(); k++) {
        BateauInfo &b = infosBateaux[k];
        visited[b.x][b.y] = true;
        for (int i = 0; i < 4; i++) {
            int nx = b.x + dx[i];
            int ny = b.y + dy[i];
            if (nx >= 0 && nx < N && ny >= 0 && ny < N)
                visited[nx][ny] = true;
        }
    }

    // Ne pas bloquer la destination
    visited[destination.first][destination.second] = false;

    queue<pair<int,int> > q;
    q.push(depart);
    visited[depart.first][depart.second] = true;

    vector<vector<pair<int,int> > > parent(N, vector<pair<int,int> >(N, make_pair(-1, -1)));

    bool found = false;

    while (!q.empty()) {
        pair<int,int> cur = q.front();
        q.pop();

        if (cur == destination) {
            found = true;
            break;
        }

        for (int i = 0; i < 4; i++) {
            int nx = cur.first  + dx[i];
            int ny = cur.second + dy[i];
            if (nx >= 0 && nx < N && ny >= 0 && ny < N && !visited[nx][ny]) {
                visited[nx][ny] = true;
                parent[nx][ny] = cur;
                q.push(make_pair(nx, ny));
            }
        }
    }

    if (!found) {
        vector<pair<int,int> > err;
        err.push_back(make_pair(-1, -1));
        return err;
    }

    vector<pair<int,int> > path;
    for (pair<int,int> cur = destination;
         cur != make_pair(-1, -1);
         cur = parent[cur.first][cur.second]) {
        path.push_back(cur);
        if (cur == depart) break;
    }

    reverse(path.begin(), path.end());
    return path;
}

int main() {
    // Test 1 : chemin direct sans obstacle
    {
        vector<BateauInfo> noBoats;
        vector<pair<int,int> > A = itineraire(make_pair(0,0), make_pair(0,4), noBoats, 5);
        cout << "Test 1 (chemin direct): ";
        for (int i = 0; i < (int)A.size(); i++)
            cout << "(" << A[i].first << "," << A[i].second << ") ";
        cout << "| taille=" << A.size() << endl;
    }

    // Test 2 : couloir etroit avec deux bateaux
    {
        vector<BateauInfo> boats;
        boats.push_back(BateauInfo("B1", 2, 0, 0));
        boats.push_back(BateauInfo("B2", 2, 4, 0));
        vector<pair<int,int> > A = itineraire(make_pair(0,2), make_pair(4,2), boats, 5);
        cout << "Test 2 (couloir etroit): ";
        for (int i = 0; i < (int)A.size(); i++)
            cout << "(" << A[i].first << "," << A[i].second << ") ";
        cout << "| taille=" << A.size() << endl;
    }

    // Test 3 : chemin bloque
    {
        vector<BateauInfo> boats;
        boats.push_back(BateauInfo("B1", 4, 3, 0));
        boats.push_back(BateauInfo("B2", 3, 4, 0));
        boats.push_back(BateauInfo("B3", 4, 2, 0));
        boats.push_back(BateauInfo("B4", 3, 3, 0));
        vector<pair<int,int> > A = itineraire(make_pair(0,0), make_pair(4,4), boats, 5);
        cout << "Test 3 (chemin bloque): ";
        for (int i = 0; i < (int)A.size(); i++)
            cout << "(" << A[i].first << "," << A[i].second << ") ";
        cout << "| taille=" << A.size() << endl;
    }

    return 0;
}