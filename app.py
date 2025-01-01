import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
from typing import Dict, Any
import plotly.express as px
import plotly.graph_objects as go

# Configuração inicial
def init_config():
    st.set_page_config(
        page_title="Controle de Veículos",
        layout="wide",
        initial_sidebar_state="expanded"
    )

# Classes para gerenciamento de dados
class DataManager:
    def __init__(self):
        self.conn = st.connection("gsheets", type=GSheetsConnection)

    def read_data(self, worksheet: str) -> pd.DataFrame:
        try:
            df = self.conn.read(worksheet=worksheet, ttl=5)
            if 'Data' in df.columns:
                df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df
        except Exception as e:
            st.error(f"Erro ao ler dados: {str(e)}")
            return pd.DataFrame()

    def add_data(self, worksheet: str, data: Dict[str, Any]) -> bool:
        try:
            df_existing = self.read_data(worksheet)
            df_new = pd.DataFrame([data])
            df_updated = pd.concat([df_existing, df_new], ignore_index=True)
            self.conn.update(worksheet=worksheet, data=df_updated)
            return True
        except Exception as e:
            st.error(f"Erro ao adicionar dados: {str(e)}")
            return False

# Componentes da UI
class FuelConsumptionUI:
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager

    def render(self):
        st.header("Registro de Consumo de Combustível")
        col1, col2 = st.columns(2)
        with col1:
            veiculo = st.selectbox("Veículo", ["Carro", "Moto"], key="fuel_vehicle")
            data_abastecimento = st.date_input("Data do Abastecimento", date.today(), key="fuel_date")
            km_atual = st.number_input("Quilometragem Atual", min_value=0.0, step=0.1, key="fuel_km")
        with col2:
            litros = st.number_input("Litros Abastecidos", min_value=0.0, step=0.1, key="fuel_liters")
            preco_litro = st.number_input("Preço por Litro", min_value=0.0, step=0.01, key="fuel_price")
            valor_total = litros * preco_litro
            st.metric("Valor Total", f"R$ {valor_total:.2f}")

        if st.button("Registrar Abastecimento", key="fuel_submit"):
            self._handle_fuel_submission(veiculo, data_abastecimento, km_atual, litros, preco_litro, valor_total)

        self._display_fuel_records()

    def _handle_fuel_submission(self, veiculo, data, km, litros, preco, valor_total):
        if km <= 0 or litros <= 0 or preco <= 0:
            st.warning("Por favor, preencha todos os campos com valores válidos.")
            return

        novo_registro = {
            "Data": data,
            "Veículo": veiculo,
            "Quilometragem": km,
            "Litros": litros,
            "Preço/L": preco,
            "Valor Total": valor_total
        }

        if self.data_manager.add_data("Consumo", novo_registro):
            st.success("Abastecimento registrado com sucesso!")
            st.rerun()

    def _display_fuel_records(self):
        st.divider()
        st.subheader("Registros de Consumo")
        dados_consumo = self.data_manager.read_data("Consumo")
        if not dados_consumo.empty:
            st.dataframe(
                dados_consumo.sort_values('Data', ascending=False),
                hide_index=True,
                use_container_width=True
            )

class MaintenanceUI:
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager

    def render(self):
        st.header("Registro de Manutenção")
        veiculo = st.selectbox("Veículo", ["Carro", "Moto"], key="maint_vehicle")
        descricao = st.text_area("Descrição da Manutenção", key="maint_desc")
        valor = st.number_input("Valor Gasto", min_value=0.0, step=0.01, key="maint_value")
        data = st.date_input("Data da Manutenção", date.today(), key="maint_date")

        if st.button("Registrar Manutenção", key="maint_submit"):
            self._handle_maintenance_submission(veiculo, descricao, valor, data)

        self._display_maintenance_records()

    def _handle_maintenance_submission(self, veiculo, descricao, valor, data):
        if not descricao or valor <= 0:
            st.warning("Por favor, preencha todos os campos com valores válidos.")
            return

        novo_registro = {
            "Data": data,
            "Veículo": veiculo,
            "Descrição": descricao,
            "Valor": valor
        }

        if self.data_manager.add_data("Manutenção", novo_registro):
            st.success("Manutenção registrada com sucesso!")
            st.rerun()

    def _display_maintenance_records(self):
        st.divider()
        st.subheader("Registros de Manutenção")
        dados_manutencao = self.data_manager.read_data("Manutenção")
        if not dados_manutencao.empty:
            st.dataframe(
                dados_manutencao.sort_values('Data', ascending=False),
                hide_index=True,
                use_container_width=True
            )

class ReportsUI:
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager

    def render(self):
        st.header("Relatórios")
        dados_consumo = self.data_manager.read_data("Consumo")
        dados_manutencao = self.data_manager.read_data("Manutenção")

        if not dados_consumo.empty:
            dados_processados = self._processar_dados_consumo(dados_consumo)
            self._render_fuel_statistics(dados_processados)
            self._render_fuel_charts(dados_consumo, dados_processados)

        if not dados_manutencao.empty:
            self._render_maintenance_statistics(dados_manutencao)
            self._render_maintenance_charts(dados_manutencao)

    def _processar_dados_consumo(self, df):
        df = df.copy()
        df = df.sort_values(['Veículo', 'Data'])
        resultado = []
        for veiculo in df['Veículo'].unique():
            df_veiculo = df[df['Veículo'] == veiculo].copy()
            df_veiculo['km_diff'] = df_veiculo['Quilometragem'].diff()
            df_veiculo['consumo_km_l'] = df_veiculo['km_diff'] / df_veiculo['Litros']
            df_veiculo = df_veiculo.dropna(subset=['consumo_km_l'])
            resultado.append(df_veiculo)
        return pd.concat(resultado) if resultado else pd.DataFrame()

    def _render_fuel_statistics(self, df):
        st.subheader("Estatísticas por Veículo")
        for veiculo in df['Veículo'].unique():
            df_veiculo = df[df['Veículo'] == veiculo]
            col1, col2, col3 = st.columns(3)
            with col1:
                custo_veiculo = df_veiculo['Valor Total'].sum()
                st.metric(f"Custo Total com Combustível - {veiculo}", f"R$ {custo_veiculo:.2f}")
            with col2:
                km_veiculo = df_veiculo['km_diff'].sum()
                st.metric(f"Quilômetros Percorridos - {veiculo}", f"{km_veiculo:.1f} km")
            with col3:
                consumo_medio = df_veiculo['consumo_km_l'].mean()
                st.metric(f"Consumo Médio - {veiculo}", f"{consumo_medio:.2f} km/L")
                
        st.subheader("Estatísticas de Consumo")
        if not df.empty:
            col1, col2 = st.columns(2)
            with col1:
                custo_total = df['Valor Total'].sum()
                st.metric("Custo Total com Combustível", f"R$ {custo_total:.2f}")
            with col2:
                km_total = df['km_diff'].sum()
                st.metric("Quilômetros Percorridos", f"{km_total:.1f} km")

    def _render_fuel_charts(self, df_original, df_processado):
        st.divider()
        st.subheader("Análise de Consumo")
        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.line(df_original.sort_values('Data'), x='Data', y='Litros', color='Veículo', title='Consumo de Combustível ao Longo do Tempo')
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            if not df_processado.empty:
                fig2 = px.line(df_processado.sort_values('Data'), x='Data', y='consumo_km_l', color='Veículo', title='Consumo (km/L) ao Longo do Tempo')
                fig2.update_layout(yaxis_title='Consumo (km/L)')
                st.plotly_chart(fig2, use_container_width=True)


    def _render_maintenance_statistics(self, df):
        st.divider()
        st.subheader("Estatísticas de Manutenção")
        gastos_por_veiculo = df.groupby('Veículo')['Valor'].sum()
        gasto_total = df['Valor'].sum()
        col1, col2, col3 = st.columns(3)
        with col1:
            for veiculo, valor in gastos_por_veiculo.items():
            # st.subheader(f"{veiculo}")
                st.metric(f"Total Gasto - {veiculo}", f"R$ {valor:.2f}")
            st.metric("Gasto Total com Manutenção", f"R$ {gasto_total:.2f}")

            with col2:
                pass
            with col3:
                fig = px.pie(df, values='Valor', names='Veículo', title='Distribuição de Gastos por Veículo')
                st.plotly_chart(fig, use_container_width=False)


    def _render_maintenance_charts(self, df):
        pass
        # st.subheader("Análise de Manutenção")
        # fig = px.pie(df, values='Valor', names='Veículo', title='Distribuição de Gastos por Veículo')
        # st.plotly_chart(fig, use_container_width=True)

def main():
    init_config()
    st.title("Controle de Veículos")
    data_manager = DataManager()

    tab1, tab2, tab3 = st.tabs(["Consumo de Combustível", "Manutenção", "Relatórios"])
    with tab1:
        fuel_ui = FuelConsumptionUI(data_manager)
        fuel_ui.render()
    with tab2:
        maintenance_ui = MaintenanceUI(data_manager)
        maintenance_ui.render()
    with tab3:
        reports_ui = ReportsUI(data_manager)
        reports_ui.render()

    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center'>
        <p>Desenvolvido com Streamlit e Google Sheets | By Leandro Costa</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
