//
//  InfoSheetView.swift
//  FocusArt
//
//  Created by Apprenant 82 on 12/03/2026.
//

import SwiftUI

struct InfoSheetView: View {
    var oeuvre: Oeuvre
    var museum : Museum
    @State private var isFavorite: Bool = false

    var body: some View {
        ScrollView{
            VStack {
                
                HStack{
                    
                    Text("• \(oeuvre.name)")
                        .font(.largeTitle)
                        .fontWeight(.black)
                        .foregroundStyle(.white)
                    Spacer()
                    Button {
                        isFavorite.toggle()
                    } label: {
                        Image(systemName: isFavorite ? "heart.fill" : "heart") 
                            .resizable()
                            .frame(width: 40, height: 40)
                            .fontWeight(.black)
                            .foregroundStyle(.yellowIcon)
                    }.padding(.vertical)
                }
                .padding(.vertical)
                Text(oeuvre.description)
                    .font(.title3)
                    .foregroundStyle(.white)
                    .fontWeight(.bold)
                    .lineSpacing(7)
                    .padding(.bottom)
                HStack {
                    Text("Oeuvres similaires")
                        .font(.largeTitle)
                        .fontWeight(.bold)
                        .foregroundStyle(.white)
                    Spacer()
                }
                
                HStack{
                    ScrollView(.horizontal){
                        HStack(spacing: 15){
                            Button{
                                
                            }label: {
                                
                                Image("derriereLaPorte")
                                    .resizable()
                                    .frame(width : 133,height :133)
                                    .cornerRadius(12)
                                    .shadow(radius:2, y:5)
                                Spacer()
                                
                            }
                            
                            Button{
                                
                            }label: {
                                Image("leVerrou")
                                    .resizable()
                                    .frame(width : 133,height :133 )
                                    .cornerRadius(12)
                                    .shadow(radius: 2, y:5)
                            }
                            Button{
                                
                            }label: {
                                Image("femmeAvecUnSac")
                                    .resizable()
                                    .frame(width : 133,height :133 )
                                    .cornerRadius(12)
                                    .shadow(radius: 2, y:5)
                            }
                            Button{
                                
                            }label: {
                                Image("leCri")
                                    .resizable()
                                    .frame(width : 133,height :133 )
                                    .cornerRadius(12)
                                    .shadow(radius: 2, y:5)
                            }
                            Button{
                                
                            }label: {
                                Image("blueMadonna")
                                    .resizable()
                                    .frame(width : 133,height :133 )
                                    .cornerRadius(12)
                                    .shadow(radius: 2, y:5)
                            }
                            
                        }
                        //.padding(.bottom)
                    }.scrollIndicators(.hidden)
                }
                
                Spacer()
                
                Button{
                    
                }label: {
                    Text("Découvrir \(museum.nom)")
                        .font(.body)
                        
                       
                }
//                .glassEffect(.regular.tint(.brown).interactive())
                .tint(.yellowIcon)
                    .foregroundStyle(.black)
                    .fontWeight(.semibold)
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)
                    .padding()
            }
            .padding()
            
        }
        
        
    }
}

#Preview {
    InfoSheetView(oeuvre: oeuvres[0],museum: museums[2])
        .background(.black)
}
