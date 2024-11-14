import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime, timedelta
from spotipy import SpotifyException
import matplotlib.pyplot as plt
import networkx as nx
import os
import sys



executable_dir = os.path.dirname(sys.executable)

#set up spotify API credentials for the app that is designed in the https://developer.spotify.com
client_id = 'PLACEHOLDER SPOTIFY DEV'
client_secret = 'PLACEHOLDER SPOTIFY DEV'
redirect_uri = 'PLACEHOLDER SPOTIFY DEV'
user_id = 'PLACEHOLDER SPOTIFY DEV'

#defiing scope to have access to the data from spotipy api and take user's tok tracks and followed artists
scope = 'user-top-read user-follow-read'
#initialise spotipy.oauth2 with the given id, secret, redirect and scope which will connec to the app that is created in https://developer.spotify.com
sp_oauth = SpotifyOAuth(client_id, client_secret, redirect_uri=redirect_uri, scope=scope)
sp = spotipy.Spotify(auth_manager=sp_oauth)


def check_token_expiry(token_info):
    if token_info and 'expires_at' in token_info:
        expires_at = token_info['expires_at']
        #if the token has expired or will expire within the next minute
        return datetime.utcnow() + timedelta(seconds=60) > datetime.utcfromtimestamp(expires_at)
    return False

#refresh the token ater checking the validity with check token expiry function
def refresh_token():
    token_info = sp_oauth.get_cached_token()
    if check_token_expiry(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
    return token_info['access_token']

#make requests to Spotify API for the next two functions which will user's token and the algorithm for token is defined above
#such that the token will be checked every 1 minute from dev.spotify.com website if it is doesn't match then update it.
def fetch_web_api(endpoint, method='GET', body=None):
    headers = {'Authorization': f'Bearer {refresh_token()}'}
    url = f'https://api.spotify.com/{endpoint}'
    response = requests.request(method, url, headers=headers, json=body)
    response.raise_for_status()  #raise exception for http/https errors while making requests from the api
    return response.json()

#ref: https://developer.spotify.com/documentation/web-api/reference/get-users-top-artists-and-tracks
def top_tracks():
    endpoint = 'v1/me/top/tracks?time_range=long_term&limit=10'
    return fetch_web_api(endpoint)['items']

top_tracks = top_tracks()
print ("\nTop listened to musics:")
for track in top_tracks:
    artists = ', '.join(artist['name'] for artist in track['artists'])
    print(f"{track['name']} by {artists}")



top_tracks_ids = [ '0o7aA8TNb6zHreGzcDsSU1','434YBNY61Y9sqBSp7OINBa','4NsPgRYUdHu2Q5JRNgXYU5','3JmGjD1CvAlGHCRNaIvxzu','3yk6FNooYqGuaked4Tm5MB' ]

#reccommend 10 new songs based on the 10 songs that we got in the part a
#ref: https://developer.spotify.com/documentation/web-api/reference/get-recommendations
def new_recommendations(top_tracks_ids):
    try:
        endpoint = f'v1/recommendations?limit=10&seed_tracks={",".join(top_tracks_ids)}' #can ask for as many reccommendations as we want by changing limit=n 
        return fetch_web_api(endpoint)['tracks']
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        return []

recommended_tracks = new_recommendations(top_tracks_ids)

print("\nNew recommended tracks:")
for track in recommended_tracks:
    artists = ', '.join(artist['name'] for artist in track['artists'])
    print(f"{track['name']} by {artists}")


def user_preferences(limit=10):
    try:
        #initialising using user top listened to tracks
        top_tracks = sp.current_user_top_tracks(limit=limit)
        
        print("\nUser Preferences:")
        for idx, track in enumerate(top_tracks['items'], start=1):
            print(f"Top Track #{idx}: {track['name']} - {', '.join(artist['name'] for artist in track['artists'])}")
    
    except SpotifyException as e: #for error handling incase it will be from the api
        print(f"Spotify API Error: {e}")
    except Exception as e:
        print(f"Error analyzing user preferences: {e}")
        

def identify_influential_users(limit=10):
    try:
        top_artists = sp.current_user_followed_artists(limit=limit)
        
        #sorting based on descending order
        sorted_artists = sorted(top_artists['artists']['items'], key=lambda x: x['followers']['total'], reverse=True)
        
        print("\nInfluential users based on followed artists:")
        for idx, artist in enumerate(sorted_artists, 1):
            print(f"{idx}. {artist['name']} - Followers: {artist['followers']['total']}")
    except SpotifyException as e:
        print(f"Spotify API Error: {e}")
    except Exception as e:
        print(f"Error identifying influential users: {e}")
        
def graph_artist_collab(artist_limit=50):
    #make a graph
    graph = nx.Graph()

    #use top artists of this user from the previous function
    top_artists = sp.current_user_top_artists(limit=artist_limit)

    for artist in top_artists['items']:
        # Add eac artist as a node
        graph.add_node(artist['name'])

        # Get the top tracks for the artist
        top_tracks = sp.artist_top_tracks(artist['id'])

        for track in top_tracks['tracks']:
            #add edges for each collaboration between artists
            for collaborator in track['artists']:
                if collaborator['name'] != artist['name']:
                    graph.add_edge(artist['name'], collaborator['name'])

    return graph

def identify_influential_artists(graph):
    # Calculate the degree centrality
    centrality = nx.degree_centrality(graph)

    # Sort the artists by centrality
    sorted_artists = sorted(centrality.items(), key=lambda x: x[1], reverse=True)

    print("\nInfluential Artists:")
    for idx, (artist, centrality) in enumerate(sorted_artists, 1):
        print(f"{idx}. {artist} - Centrality: {centrality}")

    # graph
    plt.figure(figsize=(25, 10))
    pos = nx.spring_layout(graph, k=0.15, iterations=25) #note that if you set higher iterations number, the nodes will be closer to eachother and vice versa

    #nodes
    nx.draw_networkx_nodes(graph, pos, node_size=450)

    #edges
    nx.draw_networkx_edges(graph, pos)

    #labels
    nx.draw_networkx_labels(graph, pos, font_size=8)

    plt.show()


graph = graph_artist_collab()

#in this part we see that the there is a network between the artists that shows algorithm learns from you and based o artist collabrations
def detect_communities(graph):
    communities = list(nx.community.greedy_modularity_communities(graph))
    return communities

communities = detect_communities(graph)

def calculate_centrality(graph, centrality_measure='betweenness'):
    if centrality_measure == 'betweenness':
        centrality_scores = nx.betweenness_centrality(graph)
    elif centrality_measure == 'closeness':
        centrality_scores = nx.closeness_centrality(graph)
    else:
        raise ValueError("Invalid centrality measure. Please choose 'betweenness' or 'closeness'.")
    return centrality_scores

def calculate_closeness_centrality(graph):
    
    closeness_centrality = nx.closeness_centrality(graph)
    return closeness_centrality

print("\nDetected Communities for this Graph:")
for idx, community in enumerate(communities, 1):
    print(f"Community {idx}: {community}")

def get_trending_tracks(limit=5, top_tracks_limit=10):
    try:
        #get user's playlists from the spotipy api
        featured_playlists = sp.featured_playlists(limit=limit)
        
        print("Trending Tracks:")
        for idx, playlist in enumerate(featured_playlists['playlists']['items'], 1):
            print(f"{idx}. {playlist['name']} - {playlist['owner']['display_name']}")
            
            # Get the top tracks in each playlist
            playlist_tracks = sp.playlist_tracks(playlist['id'], limit=top_tracks_limit)
            for track_idx, track in enumerate(playlist_tracks['items'], 1):
                track_info = track['track']
                artists = ', '.join(artist['name'] for artist in track_info['artists'])
                print(f"   {track_idx}. {track_info['name']} by {artists}")
    except Exception as e:
        print(f"Error getting trending tracks worldwide: {e}")


    
def user_engagement_with_artists(limit=20):
    try:
        # Fetch the most followed artists globally
        top_artists = sp.search(q='year:2024', type='artist', limit=limit)
        
        print(f"Top {limit} Influencers and Their Engagement Metrics:")
        for idx, artist in enumerate(top_artists['artists']['items'], 1):
            # Print artist details
            print(f"{idx}. {artist['name']}")
            print(f"   Followers: {artist['followers']['total']}")
            
            # Fetch top tracks for the artist
            top_tracks = sp.artist_top_tracks(artist['id'])
            total_streams = sum(track['popularity'] for track in top_tracks['tracks'])
            print(f"   Total Streams: {total_streams}")
            print()  # Add a blank line for readability
            
    except spotipy.SpotifyException as e:
        print(f"Spotify API Error: {e}")
    except Exception as e:
        print(f"Error fetching global engagement with influencers: {e}")


    
print()

def commercial_gain(limit=20):
    try:
        # Fetch the top 20 listened to artists from the Billboard playlist
        billboard_artists = []
        billboard_tracks = sp.playlist_tracks('37i9dQZF1DXcBWIGoYBM5M', limit=None)  # Fetch all tracks
        for track in billboard_tracks['items']:
            for artist in track['track']['artists']:
                if artist['name'] not in billboard_artists:
                    billboard_artists.append(artist['name'])
                    if len(billboard_artists) >= 20:
                        break
            if len(billboard_artists) >= 20:
                break
        
        # Calculate engagement using the Billboard artists
        total_followers = 0
        for artist_name in billboard_artists:
            # Fetch artist details to get follower count
            artist = sp.search(q=f"artist:{artist_name}", type='artist', limit=1)
            if artist and artist['artists'] and artist['artists']['items']:
                total_followers += artist['artists']['items'][0]['followers']['total']
        
        average_followers = total_followers / len(billboard_artists)
        
        # Initialize lists to store data for plotting
        artist_name = []
        engagement_ratios = []
        views_on_spotify = []
        
        # Example commercial exploitation strategy
        print("\nCommercial Gain Strategies:")
        for idx, artist_name in enumerate(billboard_artists, 1):
            # Fetch artist details again to get precise follower count
            artist = sp.search(q=f"artist:{artist_name}", type='artist', limit=1)
            if artist and artist['artists'] and artist['artists']['items']:
                followers_count = artist['artists']['items'][0]['followers']['total']
                engagement_ratio = followers_count / average_followers
                artist_name.append(artist_name)
                engagement_ratios.append(engagement_ratio)
                
                views_on_spotify.append(engagement_ratio * 1000)  # Just for demonstration, you can replace this with your actual data
                print(f"{idx}. {artist_name} - Followers: {followers_count}, Engagement Ratio: {engagement_ratio}")
                
        
        
        plt.figure(figsize=(10, 6))
        plt.bar(artist_name, views_on_spotify, color='skyblue')
        plt.xlabel('Artost name')
        plt.ylabel('Views')
        plt.title('Engagement Ratio vs Views on Social Media')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.show()
        
    except SpotifyException as e:
        print(f"Spotify API Error: {e}")
    except Exception as e:
        print(f"Error exploiting engagement for commercial gain: {e}")


print()

def get_top_shared_tracks():
    client_credentials_manager = sp_oauth
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

    # Get the most popular tracks globally
    top_tracks = sp.playlist_tracks('37i9dQZEVXbMDoHDwVN2tF')  # This is the Spotify playlist for the Global Top 50 tracks

    # Extract the top 10 tracks from the playlist
    top_10_shared_tracks = top_tracks['items'][:10]

    return top_10_shared_tracks

# Function to display the top 10 shared tracks
def show_top_shared_tracks(tracks):
    print("\nTop 10 Shared Tracks in the Past Month:")
    for idx, track in enumerate(tracks, 1):
        track_name = track['track']['name']
        artists = ', '.join(artist['name'] for artist in track['track']['artists'])
        print(f"{idx}. {track_name} by {artists}")



if __name__ == "__main__":
    try:
        
        top_shared_tracks = get_top_shared_tracks()
        show_top_shared_tracks(top_shared_tracks)
        
        # Get user preferences
        user_preferences()

        # Identify influential users
        identify_influential_users()

        # engagement with influencers
        user_engagement_with_artists()

        # Exploit engagement for commercial gain
        commercial_gain()

        #treding
        get_trending_tracks()
        
        
        identify_influential_artists(graph)
        
        num_nodes = len(graph.nodes)
        num_edges = len(graph.edges)

        print("\nNumber of nodes:", num_nodes)
        print("Number of edges:", num_edges)

        # Degree distribution
        degree_sequence = [d for n, d in graph.degree()]
        avg_deg = sum(degree_sequence) / num_nodes

        print("Average degree:", avg_deg)

        # Clustering coefficient
        clustering_coefficient = nx.average_clustering(graph)

        print("Clustering coefficient:", clustering_coefficient)
        
        centrality_scores = calculate_centrality(graph, centrality_measure='betweenness')
        print("\nBetweenness Centrality Scores:")
        for artist, centrality in centrality_scores.items():
            print(f"{artist}: {centrality}")
        closeness_centrality = calculate_closeness_centrality(graph)
        print("\nCloseness Centrality:")
        for node, centrality in closeness_centrality.items():
            print(f"{node}: {centrality}")
#Number of nodes and edges: There are 50 nodes (artists) in the network, connected by a total of 40 edges (collaborations between artists).

#Average degree: The average degree is 1.6, which indicates that on average, each artist collaborates with approximately 1.6 other artists. Since degrees are typically integers, this suggests that many artists have either 1 or 2 collaborations.

#Clustering coefficient: The clustering coefficient is 0.0729, which is relatively low. This suggests that the network has a relatively low level of clustering, meaning that artists' collaborations tend to form fewer tightly-knit clusters or communities.
        
    except SpotifyException as e:
        print(f"Spotify API Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
        
