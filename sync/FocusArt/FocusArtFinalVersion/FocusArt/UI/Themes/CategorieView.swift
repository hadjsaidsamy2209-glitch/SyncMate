//
//  CategorieView.swift
//  FocusArt
//
//  Created by FocusArt on 16/03/2026.
//

import SwiftUI

struct CategorieView: View {
    var categorie: Categorie
    
    let columns = [
        GridItem(.flexible(minimum: 150, maximum: 200)),
        GridItem(.flexible(minimum: 150, maximum: 200))
    ]
    
    var body: some View {
        VStack {
            HStack{
                Text(categorie.name)
                    .font(Poppins.title)
                Spacer()
            }
            .padding(.top, 80)
            .padding(.horizontal,30)
            
            ScrollView {
                LazyVGrid(columns: columns, spacing: 26) {
                    ForEach(oeuvres.filter({ $0.categorie.name == categorie.name })) { oeuvre in
                        NavigationLink(destination: OeuvreDescription(oeuvre: oeuvre, museum: museums[0])) {
                            VStack(alignment: .center, spacing: 6) {
                                Image(oeuvre.image)
                                    .resizable()
                                    .scaledToFill()
                                    .frame(width: 153, height: 153)
                                    .cornerRadius(12)
//                                    .shadow(radius: 2, y:3)
                                    .clipped()
                                Text(oeuvre.name)
                                    .font(Poppins.body)
                                    .foregroundStyle(.primary)
                                    .lineLimit(1)
                                
                            }
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                }
                .padding()
            }
            
            
            .toolbar(.hidden, for: .tabBar)
            //.navigationBarTitleDisplayMode(.large)
        }
        .background(Color.whiteBackground)
        .ignoresSafeArea()
    }
}

#Preview {
        CategorieView(categorie: categories[2])
    
}
