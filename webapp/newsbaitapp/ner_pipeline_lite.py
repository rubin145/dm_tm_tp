import io
import zipfile
import pandas as pd

def get_entities_in_doc(unique_id, unified_entities_docs):
    entities = [entity for entity, indices in unified_entities_docs.items() if unique_id in indices['docs']]
    return entities

# Given a representative tag, fetch synonyms
def get_synonyms_for_tag(tag,unified_to_raw):
    return unified_to_raw.get(tag, [])

def ner_pipeline(csv_file, params):
    npl = NERPipelineLite(csv_file, **params)
    npl.process()
    return npl.get_zip_buffer()

class NERPipelineLite:
    def __init__(self, file, **params):
        self.df_news = pd.read_csv(file)
        
        self.docs_field = params.get('docs_field', 'texto')
        self.section = params.get('section', '')
        self.ner_model = params.get('ner_model', "es_core_news_md")
        self.embedding = params.get('embedding', "fasttext")
        self.clustering_alg = params.get('clustering_alg', "hierarchical")
        self.hier_threshold = params.get('hier_threshold', 0.9)
        self.dbs_eps = params.get('dbs_eps', 0.1)
        self.dbs_min_samples = params.get('dbs_min_samples', 5)
        
        self.docs = [(doc, uid) for doc, uid in zip(self.df_news[self.docs_field], self.df_news['unique_id']) if isinstance(doc, str)]
        self.summary = f'nombre del archivo input: {file.name}\ncant de documentos: {len(self.docs)}'
        self.raw_entities = {}
        self.filtered_entities = {}
        self.unified_entities_docs = {}
        self.unified_to_raw = {}
        self.embedding_model = None

    def process(self):
        self.get_raw_entities()
        self.filter_entities()
        self.unify_entities()
        self.make_df()

    def get_raw_entities(self):
        nlp = self.lazy_load_spacy() if self.ner_model == "es_core_news_md" else None
        ner_analyzer = self.lazy_load_pysentimiento() if self.ner_model == "robertuito" else None
        for doc, uid in self.docs:
            if nlp:
                processed_doc = nlp(doc)
                self.extract_entities(processed_doc, uid)
            elif ner_analyzer:
                entities = ner_analyzer.predict(doc)
                for ent in entities:
                    self.add_entity(ent['text'], uid, self.raw_entities)
        self.summary += f'\ncant de entidades (incluye repeticiones): {len(self.raw_entities)}'

    def filter_entities(self):
        nlp = self.lazy_load_spacy() if self.ner_model == "es_core_news_md" else None
        for entity, data in self.raw_entities.items():
            if nlp:
                postprocessed_entity = ' '.join([token.text for token in nlp(entity) if token.pos_ in ["NOUN", "PROPN"]])
            else:
                postprocessed_entity = entity  # Placeholder for pysentimiento filtering
            if postprocessed_entity:
                self.add_entity(postprocessed_entity, data['occurrences'], data['docs'], self.filtered_entities)
        self.summary += f'\ncant de entidades (filtradas): {len(self.filtered_entities)}'

    def unify_entities(self):
        if self.clustering_alg == 'hierarchical':
            self.filtered_to_unified, info = self.get_unified_entities_hierarchical()
        elif self.clustering_alg == 'dbscan':
            self.filtered_to_unified, info = self.get_unified_entities_dbscan()
        self.summary += f'\n{info}'
        self.map_unified_entities()

    def make_df(self):
        tags = []
        doc_ids = []
        appearances = []
        occurrences = []
        sections = []

        for entity, data in self.unified_entities_docs.items():
            tags.append(entity)
            doc_ids.append(list(data['docs']))
            appearances.append(len(data['docs']))
            occurrences.append(data['occurrences'])
            sections.append(self.section) 

        self.df = pd.DataFrame({
            'Tag': tags,
            'Document IDs': doc_ids,
            'Appearances': appearances,
            'Occurrences': occurrences,
            'Section': sections
        })

        self.df['Synonyms'] = self.df['Tag'].apply(lambda x: get_synonyms_for_tag(x, self.unified_to_raw))
        self.df['n_Synonyms'] = self.df['Synonyms'].apply(len)
        # Sort the DataFrame by Appearances in descending order
        self.df = self.df.sort_values(by='Appearances', ascending=False).reset_index(drop=True)

        #pd.set_option('display.max_colwidth', 200)

    def get_embeddings(self, text_list):
        if self.embedding == 'fasttext' and not self.embedding_model:
            self.embedding_model = self.lazy_load_fasttext()
        elif self.embedding == 'robertuito' and not self.embedding_model:
            tokenizer, model = self.lazy_load_transformers()
            self.embedding_model = lambda text: self.get_transformer_embedding(tokenizer, model, text)

        return [self.embedding_model(text) for text in text_list]
    
    def get_transformer_embedding(self, tokenizer, model, text):
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        outputs = model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).detach().numpy()

    def get_unified_entities_hierarchical(self):
        from scipy.cluster.hierarchy import linkage, fcluster
        from scipy.spatial.distance import cdist
        from numpy import mean, argmin

        raw_entities_list = list(self.filtered_entities.keys())
        entity_vectors = self.get_embeddings(raw_entities_list)

        # Hierarchical clustering
        Z = linkage(entity_vectors, method='average', metric='cosine')
        clusters = fcluster(Z, t=self.hier_threshold, criterion='distance')

        return self.cluster_entities(raw_entities_list, entity_vectors, clusters)

    def get_unified_entities_dbscan(self):
        from sklearn.cluster import DBSCAN
        import numpy as np

        raw_entities_list = list(self.filtered_entities.keys())
        entity_vectors = np.array(self.get_embeddings(raw_entities_list))

        # DBSCAN clustering
        dbscan = DBSCAN(eps=self.dbs_eps, min_samples=self.dbs_min_samples, metric='cosine')
        dbscan.fit(entity_vectors)

        return self.cluster_entities(raw_entities_list, entity_vectors, dbscan.labels_)

    def cluster_entities(self, raw_entities_list, entity_vectors, labels):
        from numpy import mean, argmin
        from scipy.spatial.distance import cdist

        clustered_entities = {}
        raw_to_unified = {}

        # Determine cluster vectors outside the loop
        cluster_vectors = entity_vectors
        if self.embedding == 'fasttext':
            cluster_vectors = [entity_vectors[idx] for idx, entity in enumerate(raw_entities_list)]

        for idx, cluster_id in enumerate(labels):
            if cluster_id not in clustered_entities:
                clustered_entities[cluster_id] = []
            clustered_entities[cluster_id].append(raw_entities_list[idx])

        # Map raw entities to their representative
        for cluster_id, entities_in_cluster in clustered_entities.items():
            if entities_in_cluster:  # Check if there are entities in the cluster
                mean_vector = mean(cluster_vectors, axis=0)
                distances = cdist([mean_vector], cluster_vectors, 'cosine')
                closest_index = argmin(distances)
                representative = entities_in_cluster[closest_index]
                for entity in entities_in_cluster:
                    raw_to_unified[entity] = representative

        info = f'número de entidades agrupadas: {len(clustered_entities.keys())}'
        return raw_to_unified, info

    def lazy_load_spacy(self):
        import spacy
        return spacy.load(self.ner_model)

    def lazy_load_pysentimiento(self):
        from pysentimiento import create_analyzer
        return create_analyzer("ner", lang="es")

    def lazy_load_fasttext(self):
        import fasttext
        return fasttext.load_model('cc.es.300.bin')

    def lazy_load_transformers(self):
        from transformers import AutoTokenizer, AutoModel
        tokenizer = AutoTokenizer.from_pretrained('robertuito-base-cased')
        model = AutoModel.from_pretrained('robertuito-base-cased')
        return tokenizer, model

    def extract_entities(self, processed_doc, uid):
        for ent in processed_doc.ents:
            self.add_entity(ent.text.replace('\n', ''), uid)

    def add_entity(self, entity_text, uid, entity_dict):
        if entity_text not in entity_dict:
            entity_dict[entity_text] = {'occurrences': 0, 'docs': set()}
        entity_dict[entity_text]['occurrences'] += 1
        entity_dict[entity_text]['docs'].add(uid)

    def map_unified_entities(self):
        # Iterate over the filtered entities and their data
        for filtered_entity, data in self.filtered_entities.items():
            # Get the unified entity for the current filtered entity
            unified_entity = self.filtered_to_unified.get(filtered_entity)
            # If the unified entity is not in the unified_entities_docs, add it
            if unified_entity not in self.unified_entities_docs:
                self.unified_entities_docs[unified_entity] = {'docs': set(), 'occurrences': 0}
            # Update the occurrences and docs for the unified entity
            self.unified_entities_docs[unified_entity]['occurrences'] += data['occurrences']
            self.unified_entities_docs[unified_entity]['docs'].update(data['docs'])
            # Also, map the unified entity back to the raw entities for synonym purposes
            if unified_entity not in self.unified_to_raw:
                self.unified_to_raw[unified_entity] = []
            self.unified_to_raw[unified_entity].append(filtered_entity)

    def get_zip_buffer(self):
        entities_csv = self.df.to_csv(index=False)
        news_csv = self.df_news.to_csv(index=False)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zip_file:
            zip_file.writestr('news.csv', news_csv)
            zip_file.writestr('entities.csv', entities_csv)
            zip_file.writestr('summary.txt', self.summary)
        buffer.seek(0)
        return buffer