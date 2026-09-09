// Bounded reference export: calls TEMPO2 directly, with no fit or search.
#include <tempo2.h>
#include <t2fit.h>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <vector>
#include <string>

double t2FitFunc_nestlike_red(pulsar*,int,double,int,param_label,int);
double t2FitFunc_nestlike_red_dm(pulsar*,int,double,int,param_label,int);
double constraints_nestlike_red(pulsar*,int,int,int,int,int,void*);
double constraints_nestlike_red_dm(pulsar*,int,int,int,int,int,void*);

extern "C" const char *plugVersionCheck = TEMPO2_h_VER;
extern "C" int graphicalInterface(int argc,char *argv[],pulsar *psr,int *npsr) {
    char par[1][MAX_FILELEN] = {}, tim[1][MAX_FILELEN] = {};
    const char *out = nullptr;
    for(int i=1;i<argc;i++) {
        if(!strcmp(argv[i],"-f") && i+2<argc) {
            snprintf(par[0],MAX_FILELEN,"%s",argv[++i]);
            snprintf(tim[0],MAX_FILELEN,"%s",argv[++i]);
        } else if(!strcmp(argv[i],"-export") && i+1<argc) out=argv[++i];
    }
    if(!out || !par[0][0] || !tim[0][0]) return 2;
    *npsr=1;
    readParfile(psr,par,tim,1); readTimfile(psr,tim,1);
    if(psr[0].param[param_pb].paramSet[0]) return 3;
    preProcess(psr,1,0,nullptr); formBatsAll(psr,1); formResiduals(psr,1,1);
    FILE *f=fopen(out,"w"); if(!f) return 4;
    fprintf(f,"# sat bat bbat residual_seconds scaled_error_us freqSSB_Hz deleted\n");
    std::string previous_chain;
    for(int i=0;i<psr[0].nobs;i++) {
        const auto &o=psr[0].obsn[i];
        fprintf(f,"%.21Lg %.21Lg %.21Lg %.21Lg %.17g %.17g %d\n",
                o.sat,o.bat,o.bbat,o.residual,o.toaErr,o.freqSSB,o.deleted);
        std::string chain(o.telID);
        for(int j=0;j<o.nclock_correction;j++) chain += std::string(" ")+o.correctionsTT[j].corrects_to;
        if(chain!=previous_chain) {
            printf("CLOCK_CHAIN %s\n",chain.c_str());
            previous_chain=chain;
        }
    }
    fclose(f);
    // Use TEMPO2's own Fourier derivatives and prior-constraint functions.
    for(int dm=0;dm<2;dm++) {
        const int n=psr[0].nobs, modes=dm?psr[0].TNDMC:psr[0].TNRedC;
        // Export weighted Fourier factors, avoiding quadratic text output.
        std::vector<double> factors(n*2*modes,0);
        for(int k=0;k<modes;k++) {
            const auto s=dm?param_red_dm_sin:param_red_sin;
            const auto co=dm?param_red_dm_cos:param_red_cos;
            const int constraint=dm?constraint_red_dm_sin:constraint_red_sin;
            const double precision=dm?constraints_nestlike_red_dm(psr,0,constraint,s,k,k,nullptr):constraints_nestlike_red(psr,0,constraint,s,k,k,nullptr);
            for(int i=0;i<n;i++) {
                const double x=psr[0].obsn[i].bbat-psr[0].param[param_pepoch].val[0];
                factors[i*2*modes+2*k]=(dm?t2FitFunc_nestlike_red_dm(psr,0,x,i,s,k):t2FitFunc_nestlike_red(psr,0,x,i,s,k))/precision;
                factors[i*2*modes+2*k+1]=(dm?t2FitFunc_nestlike_red_dm(psr,0,x,i,co,k):t2FitFunc_nestlike_red(psr,0,x,i,co,k))/precision;
            }
        }
        char filename[MAX_FILELEN]; snprintf(filename,sizeof(filename),"%s.%s",out,dm?"dm":"red");
        f=fopen(filename,"w"); if(!f) return 4;
        for(int i=0;i<n;i++) {for(int j=0;j<2*modes;j++) fprintf(f,"%.17g%c",factors[i*2*modes+j],j+1==2*modes?'\n':' ');}
        fclose(f);
    }
    // Obtain ECORR epoch membership and prior directly from the installed fit code.
    const int n=psr[0].nobs;
    std::vector<double> x(n),y(n),e(n); std::vector<int> idx(n);
    unsigned int nd=t2Fit_getFitData(psr,x.data(),y.data(),e.data(),idx.data());
    char included_filename[MAX_FILELEN];
    snprintf(included_filename,sizeof(included_filename),"%s.included",out);
    f=fopen(included_filename,"w"); if(!f) return 4;
    for(unsigned int i=0;i<nd;i++) fprintf(f,"%d\n",idx[i]);
    fclose(f);
    FitInfo globals = {}, fit = {};
    t2Fit_fillGlobalFitInfo(psr,1,globals);
    t2Fit_fillFitInfo(psr,fit,globals,x.data(),idx.data(),nd);
    char filename[MAX_FILELEN]; snprintf(filename,sizeof(filename),"%s.ecorr",out);
    f=fopen(filename,"w"); if(!f) return 4;
    for(int k=0;k<fit.nParams;k++) if(fit.paramIndex[k]==param_jitter) {
        const int anchor=fit.paramCounters[k];
        double precision=0;
        for(int c=0;c<fit.nConstraints;c++) if(fit.constraintIndex[c]==constraint_jitter && fit.constraintCounters[c]==anchor)
            precision=fit.constraintDerivs[c](psr,0,fit.constraintIndex[c],param_jitter,anchor,anchor,nullptr);
        if(!(precision>0)) return 5;
        for(int i=0;i<n;i++) if(fit.paramDerivs[k](psr,0,0,i,param_jitter,anchor)!=0)
            fprintf(f,"%d %d %.17g\n",anchor,i,1/precision);
    }
    fclose(f);
    printf("REFERENCE_COMPLETE %d NO_FIT_NO_SEARCH\n",psr[0].nobs);
    return 0;
}
