import streamlit as st
from datetime import date, timedelta

# Configuração da Página
st.set_page_config(page_title="Calculadora de Rescisão CLT", page_icon="📝")

st.title("📝 Simulador de Rescisão de Contrato")
st.markdown("Calcule as verbas rescisórias estimadas conforme a CLT.")

# --- BARRA LATERAL (INPUTS) ---
with st.sidebar:
    st.header("Dados do Contrato")
    salario_base = st.number_input("Último Salário Bruto (R$)", min_value=0.0, value=3000.00, step=100.00)
    data_admissao = st.date_input("Data de Admissão", value=date(2022, 1, 10))
    data_demissao = st.date_input("Data de Saída (Último dia)", value=date.today())
    
    motivo = st.selectbox(
        "Motivo da Rescisão",
        ["Dispensa sem Justa Causa", "Pedido de Demissão", "Justa Causa"]
    )
    
    aviso_previo = st.radio("Aviso Prévio", ["Trabalhado", "Indenizado", "Não cumpriu (Descontar)"])
    
    saldo_fgts = st.number_input("Saldo atual do FGTS (R$)", min_value=0.0, value=0.0)
    tem_ferias_vencidas = st.checkbox("Possui férias vencidas (1 ano completo sem tirar)?")

# --- LÓGICA DE CÁLCULO ---

def calcular_rescisao():
    # 1. Validações básicas
    if data_demissao < data_admissao:
        st.error("A data de demissão não pode ser anterior à admissão!")
        return None

    # Tempo de Casa (em anos e meses)
    tempo_total = data_demissao - data_admissao
    anos_completos = tempo_total.days // 365
    
    verbas = {}
    descontos = {}
    
    # 2. Saldo de Salário
    # Dias trabalhados no mês da demissão
    dias_trabalhados = data_demissao.day
    valor_dia = salario_base / 30
    verbas["Saldo de Salário"] = valor_dia * dias_trabalhados

    # 3. Aviso Prévio (Lei 12.506/2011)
    # 30 dias + 3 dias por ano completo (limite de 90 dias)
    dias_aviso = min(30 + (3 * anos_completos), 90)
    valor_aviso = valor_dia * dias_aviso

    # Lógica do Aviso
    if motivo == "Dispensa sem Justa Causa":
        if aviso_previo == "Indenizado":
            verbas[f"Aviso Prévio Indenizado ({dias_aviso} dias)"] = valor_aviso
            # Projeção do aviso no tempo de serviço para férias/13º
            data_projecao = data_demissao + timedelta(days=dias_aviso)
        else:
            # Trabalhado já está pago no saldo ou mês anterior, mas afeta a data final
            data_projecao = data_demissao
            
    elif motivo == "Pedido de Demissão":
        data_projecao = data_demissao
        if aviso_previo == "Não cumpriu (Descontar)":
            descontos["Desconto de Aviso Prévio (30 dias)"] = salario_base

    elif motivo == "Justa Causa":
        data_projecao = data_demissao
        # Justa causa perde quase tudo

    # 4. Décimo Terceiro Proporcional
    # Conta meses a partir de Janeiro do ano da saída até a data projetada
    # Fração >= 15 dias conta como mês inteiro
    meses_13 = 0
    start_date = date(data_projecao.year, 1, 1)
    
    # Se a projeção virou o ano, calcula o ano todo de saída, mas vamos simplificar para o ano corrente
    # Lógica simplificada: Meses trabalhados no ano
    if data_projecao.year > data_demissao.year:
        # Caso raro de aviso virando ano, simplificamos para fins didáticos
        pass
    
    # Contagem de meses para 13º
    mes_saida = data_projecao.month
    dia_saida = data_projecao.day
    meses_13 = mes_saida if dia_saida >= 15 else mes_saida - 1
    
    if motivo != "Justa Causa":
        verbas[f"13º Salário Proporcional ({meses_13}/12)"] = (salario_base / 12) * meses_13

    # 5. Férias
    # Férias Vencidas
    if tem_ferias_vencidas and motivo != "Justa Causa":
        verbas["Férias Vencidas"] = salario_base
        verbas["1/3 Sobre Férias Vencidas"] = salario_base / 3
        
    # Férias Proporcionais (Conta do aniversário da admissão até a projeção)
    # Lógica simplificada de meses proporcionais
    # Pega o mês de admissão e conta até a saída
    # (Cálculo exato de férias requer histórico de períodos aquisitivos, usaremos aproximação pelo mês)
    # Vamos assumir que o período aquisitivo zerou no último aniversário da admissão
    
    ultimo_aniversario = date(data_projecao.year, data_admissao.month, data_admissao.day)
    if ultimo_aniversario > data_projecao:
        ultimo_aniversario = date(data_projecao.year - 1, data_admissao.month, data_admissao.day)
        
    dias_periodo_aquisitivo = (data_projecao - ultimo_aniversario).days
    meses_ferias = dias_periodo_aquisitivo // 30 # Aproximação
    # Ajuste fino: se a sobra de dias for >= 14
    if (dias_periodo_aquisitivo % 30) >= 14:
        meses_ferias += 1
    meses_ferias = min(meses_ferias, 12)

    if motivo != "Justa Causa":
        valor_ferias_prop = (salario_base / 12) * meses_ferias
        verbas[f"Férias Proporcionais ({meses_ferias}/12)"] = valor_ferias_prop
        verbas["1/3 Sobre Férias Proporcionais"] = valor_ferias_prop / 3

    # 6. Multa FGTS (40%)
    if motivo == "Dispensa sem Justa Causa":
        multa_fgts = saldo_fgts * 0.40
        verbas["Multa 40% FGTS"] = multa_fgts

    return verbas, descontos, anos_completos

# --- INTERFACE DE RESULTADOS ---

if st.button("Calcular Rescisão 💼"):
    resultado = calcular_rescisao()
    
    if resultado:
        verbas, descontos, anos = resultado
        
        st.divider()
        st.subheader(f"Resultado Estimado (Tempo de Casa: {anos} anos)")
        
        col1, col2 = st.columns(2)
        
        total_proventos = sum(verbas.values())
        total_descontos = sum(descontos.values())
        liquido = total_proventos - total_descontos
        
        with col1:
            st.markdown("### ✅ Proventos")
            for item, valor in verbas.items():
                st.write(f"➕ {item}: **R$ {valor:,.2f}**")
            st.markdown(f"**Total Proventos: R$ {total_proventos:,.2f}**")
            
        with col2:
            st.markdown("### 🔻 Descontos")
            if descontos:
                for item, valor in descontos.items():
                    st.write(f"➖ {item}: **R$ {valor:,.2f}**")
            else:
                st.write("Sem descontos específicos (INSS/IRRF sobre rescisão não inclusos nesta simulação simplificada).")
            st.markdown(f"**Total Descontos: R$ {total_descontos:,.2f}**")
        
        st.success(f"### 💰 Valor Líquido Estimado: R$ {liquido:,.2f}")
        st.info("⚠️ Nota: Este cálculo é uma estimativa e não substitui o cálculo oficial do RH/Contabilidade. Incidências de INSS/IRRF sobre verbas rescisórias variam conforme a natureza de cada rubrica.")

else:
    st.info("Preencha os dados ao lado para simular.")
